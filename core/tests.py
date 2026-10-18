import importlib
import shutil
import tempfile
from unittest import mock

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from .forms import AnalisePeiForm, EditarPeiForm, NovaVersaoPeiForm
from .models import HistoricoPei, Notificacao, Pei, TransicaoPeiInvalida

MEDIA_TESTE = tempfile.mkdtemp(prefix='napne-testes-media-')
PRIVADO_TESTE = tempfile.mkdtemp(prefix='napne-testes-privado-')

# Hash de senha rápido só nos testes (o padrão do Django é lento de propósito e multiplicava o tempo da suíte).
HASH_RAPIDO = ['django.contrib.auth.hashers.MD5PasswordHasher']


def usuario(username, grupo=None):
    novo = get_user_model().objects.create_user(username=username, password='senha-forte-123', first_name=username.title())
    if grupo:
        novo.groups.add(Group.objects.get_or_create(name=grupo)[0])
    return novo


def arquivo_pdf(nome='pei.pdf', conteudo=b'%PDF-1.4 conteudo de teste'):
    return SimpleUploadedFile(nome, conteudo, content_type='application/pdf')


def criar_pei(professor, titulo='PEI de Matemática', **extra):
    return Pei.objects.create(titulo=titulo, arquivo=arquivo_pdf(), professor=professor, **extra)

@override_settings(MEDIA_ROOT=MEDIA_TESTE, PEI_ARMAZENAMENTO_PRIVADO=PRIVADO_TESTE, PASSWORD_HASHERS=HASH_RAPIDO)
class BaseTestes(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TESTE, ignore_errors=True)
        shutil.rmtree(PRIVADO_TESTE, ignore_errors=True)

    def setUp(self):
        self.professor = usuario('prof', 'Servidor')
        self.outro_professor = usuario('prof2', 'Servidor')
        self.estudante = usuario('aluno', 'Estudante')
        self.napne = usuario('napne1', 'NAPNE')
        self.pendente = usuario('pendente')  # pediu para entrar no NAPNE, mas ainda não foi aprovado
        self.pei = criar_pei(self.professor)


class FluxoDeAnaliseDoModeloTests(BaseTestes):
    def test_todo_pei_nasce_com_a_versao_1(self):
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        versao = self.pei.versao_atual
        self.assertEqual(versao.numero, 1)
        self.assertEqual(versao.arquivo.name, self.pei.arquivo.name)
        self.assertEqual(versao.enviado_por, self.professor)

    def test_aprovar_sem_parecer_deixa_o_pei_analisado_e_grava_o_historico(self):
        historico = self.pei.registrar_analise(Pei.DECISAO_APROVAR, '', self.napne)

        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.ANALISADO)
        self.assertEqual(historico.status_anterior, Pei.EM_ANALISE)
        self.assertEqual(historico.status_novo, Pei.ANALISADO)
        self.assertEqual(historico.alterado_por, self.napne)
        self.assertEqual(historico.observacao, '')
        self.assertIsNotNone(historico.alterado_em)
        self.assertEqual(historico.versao, self.pei.versao_atual)

    def test_devolver_e_solicitar_ajustes_gravam_o_parecer(self):
        casos = [
            (Pei.DECISAO_DEVOLVER, Pei.DEVOLVIDO),
            (Pei.DECISAO_AJUSTES, Pei.AJUSTES_SOLICITADOS),
        ]
        for decisao, esperado in casos:
            with self.subTest(decisao=decisao):
                pei = criar_pei(self.professor, titulo=f'PEI {decisao}')
                historico = pei.registrar_analise(decisao, '  Faltou o plano de avaliação.  ', self.napne)
                pei.refresh_from_db()
                self.assertEqual(pei.status, esperado)
                self.assertEqual(historico.observacao, 'Faltou o plano de avaliação.')
                self.assertEqual(historico.alterado_por, self.napne)

    def test_parecer_e_obrigatorio_ao_devolver_ou_solicitar_ajustes(self):
        for decisao in (Pei.DECISAO_DEVOLVER, Pei.DECISAO_AJUSTES):
            for parecer in ('', '   ', None):
                with self.subTest(decisao=decisao, parecer=parecer):
                    with self.assertRaises(ValidationError):
                        self.pei.registrar_analise(decisao, parecer, self.napne)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        self.assertFalse(self.pei.historico.exists())
        self.assertFalse(Notificacao.objects.exists())

    def test_so_e_possivel_decidir_em_pei_em_analise(self):
        for status in (Pei.ANALISADO, Pei.DEVOLVIDO, Pei.AJUSTES_SOLICITADOS):
            with self.subTest(status=status):
                Pei.objects.filter(pk=self.pei.pk).update(status=status)
                self.pei.refresh_from_db()
                with self.assertRaises(TransicaoPeiInvalida):
                    self.pei.registrar_analise(Pei.DECISAO_APROVAR, '', self.napne)
        self.assertFalse(self.pei.historico.exists())

    def test_decisao_desconhecida_e_recusada(self):
        with self.assertRaises(ValueError):
            self.pei.registrar_analise('talvez', 'x', self.napne)

    def test_a_decisao_usa_o_status_do_banco_e_nao_o_da_instancia_antiga(self):
        """Duas pessoas com a tela aberta: a segunda decisão não pode sobrescrever a primeira."""
        copia_antiga = Pei.objects.get(pk=self.pei.pk)
        self.pei.registrar_analise(Pei.DECISAO_APROVAR, '', self.napne)
        with self.assertRaises(TransicaoPeiInvalida):
            copia_antiga.registrar_analise(Pei.DECISAO_DEVOLVER, 'Devolvendo tarde demais', self.napne)
        self.assertEqual(self.pei.historico.count(), 1)

    def test_a_decisao_notifica_o_professor_com_link_direto_e_sem_expor_o_parecer(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Parecer confidencial sobre o aluno.', self.napne)

        notificacao = Notificacao.objects.get()
        self.assertEqual(notificacao.destino_tipo, Notificacao.USUARIO)
        self.assertEqual(notificacao.destinatario, self.professor)
        self.assertEqual(notificacao.remetente, self.napne)
        self.assertEqual(notificacao.link, reverse('detalhar_meu_pei', args=[self.pei.id]))
        self.assertIn('devolvido', notificacao.titulo.lower())
        self.assertNotIn('confidencial', notificacao.conteudo)
        self.assertNotIn('confidencial', notificacao.titulo)

    def test_titulo_da_notificacao_respeita_o_limite_do_campo(self):
        pei = criar_pei(self.professor, titulo='T' * 100)
        pei.registrar_analise(Pei.DECISAO_APROVAR, '', self.napne)
        self.assertLessEqual(len(Notificacao.objects.get().titulo), 100)

    def test_se_a_notificacao_falhar_nada_e_gravado(self):
        with mock.patch.object(Notificacao.objects, 'create', side_effect=RuntimeError('falha')):
            with self.assertRaises(RuntimeError):
                self.pei.registrar_analise(Pei.DECISAO_APROVAR, '', self.napne)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        self.assertFalse(self.pei.historico.exists())


class NovaVersaoDoModeloTests(BaseTestes):
    def devolver(self, decisao=Pei.DECISAO_DEVOLVER):
        self.pei.registrar_analise(decisao, 'Corrija o item 3.', self.napne)

    def test_nova_versao_cria_a_versao_2_e_volta_para_em_analise(self):
        self.devolver()
        arquivo_v1 = self.pei.arquivo.name

        historico = self.pei.enviar_nova_versao(arquivo_pdf('corrigido.pdf', b'%PDF-1.4 v2'), self.professor, 'Ajustei o item 3.')

        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        self.assertEqual([v.numero for v in self.pei.versoes.all()], [1, 2])
        self.assertEqual(self.pei.versao_atual.numero, 2)
        self.assertEqual(self.pei.arquivo.name, self.pei.versao_atual.arquivo.name)
        self.assertNotEqual(self.pei.arquivo.name, arquivo_v1)
        self.assertEqual(historico.status_anterior, Pei.DEVOLVIDO)
        self.assertEqual(historico.status_novo, Pei.EM_ANALISE)
        self.assertEqual(historico.alterado_por, self.professor)
        self.assertEqual(historico.observacao, 'Ajustei o item 3.')
        self.assertEqual(historico.versao.numero, 2)

    def test_versoes_anteriores_continuam_consultaveis(self):
        self.devolver()
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf', b'%PDF-1.4 v2'), self.professor)
        primeira = self.pei.versoes.get(numero=1)
        self.assertEqual(primeira.arquivo.read(), b'%PDF-1.4 conteudo de teste')

    def test_funciona_tambem_apos_solicitar_ajustes(self):
        self.devolver(Pei.DECISAO_AJUSTES)
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf'), self.professor)
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)

    def test_so_e_possivel_enviar_nova_versao_de_pei_devolvido_ou_com_ajustes(self):
        for status in (Pei.EM_ANALISE, Pei.ANALISADO):
            with self.subTest(status=status):
                Pei.objects.filter(pk=self.pei.pk).update(status=status)
                self.pei.refresh_from_db()
                with self.assertRaises(TransicaoPeiInvalida):
                    self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf'), self.professor)
        self.assertEqual(self.pei.versoes.count(), 1)

    def test_outro_professor_nao_pode_enviar_versao(self):
        self.devolver()
        with self.assertRaises(PermissionDenied):
            self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf'), self.outro_professor)
        self.assertEqual(self.pei.versoes.count(), 1)

    def test_ciclo_completo_com_duas_correcoes(self):
        self.devolver()
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf'), self.professor)
        self.pei.registrar_analise(Pei.DECISAO_AJUSTES, 'Ainda falta o cronograma.', self.napne)
        self.pei.enviar_nova_versao(arquivo_pdf('v3.pdf'), self.professor, 'Incluí o cronograma.')
        self.pei.registrar_analise(Pei.DECISAO_APROVAR, 'Aprovado.', self.napne)

        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.ANALISADO)
        self.assertEqual([v.numero for v in self.pei.versoes.all()], [1, 2, 3])
        self.assertEqual(
            [h.status_novo for h in self.pei.historico.all()],
            [Pei.DEVOLVIDO, Pei.EM_ANALISE, Pei.AJUSTES_SOLICITADOS, Pei.EM_ANALISE, Pei.ANALISADO],
        )
        self.assertEqual(Notificacao.objects.count(), 3)  # uma por decisão do NAPNE

    def test_descricao_do_evento_no_historico(self):
        self.devolver()
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf'), self.professor)
        self.pei.registrar_analise(Pei.DECISAO_APROVAR, '', self.napne)
        descricoes = [h.descricao_evento() for h in self.pei.historico.all()]
        self.assertEqual(descricoes, [
            'PEI devolvido pelo NAPNE',
            'Nova versão enviada pelo professor',
            'Análise concluída pelo NAPNE',
        ])


class FormulariosDoFluxoTests(TestCase):
    def test_analise_exige_decisao(self):
        form = AnalisePeiForm(data={'parecer': 'x'})
        self.assertFalse(form.is_valid())
        self.assertIn('Escolha uma decisão', form.errors['decisao'][0])

    def test_parecer_obrigatorio_ao_devolver_e_ao_solicitar_ajustes(self):
        for decisao in (Pei.DECISAO_DEVOLVER, Pei.DECISAO_AJUSTES):
            form = AnalisePeiForm(data={'decisao': decisao, 'parecer': '   '})
            self.assertFalse(form.is_valid(), decisao)
            self.assertEqual(form.errors['parecer'], ['O parecer é obrigatório ao devolver ou solicitar ajustes.'])

    def test_parecer_opcional_ao_aprovar(self):
        form = AnalisePeiForm(data={'decisao': Pei.DECISAO_APROVAR, 'parecer': ''})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['parecer'], '')

    def test_parecer_tem_limite_de_tamanho(self):
        form = AnalisePeiForm(data={'decisao': Pei.DECISAO_APROVAR, 'parecer': 'a' * 2001})
        self.assertFalse(form.is_valid())
        self.assertIn('no máximo 2000', form.errors['parecer'][0])

    def test_decisao_invalida(self):
        form = AnalisePeiForm(data={'decisao': 'analizado'})
        self.assertFalse(form.is_valid())

    def test_nova_versao_exige_arquivo(self):
        form = NovaVersaoPeiForm(data={}, files={})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['arquivo'], ['Selecione o arquivo corrigido do PEI.'])

    def test_edicao_do_pei_nunca_inclui_o_arquivo(self):
        campos = list(EditarPeiForm().fields)
        self.assertNotIn('arquivo', campos)
        self.assertEqual(campos, ['titulo', 'estudante_nome', 'estudante_matricula', 'estudante_curso', 'periodo_letivo'])


class AnaliseNoPainelTests(BaseTestes):
    def url_detalhe(self):
        return reverse('detalhar_pei', args=[self.pei.id])

    def test_matriz_de_acesso_ao_detalhe_e_a_analise(self):
        casos = [
            ('visitante', None, 302),
            ('estudante', self.estudante, 403),
            ('professor', self.professor, 403),
            ('napne pendente', self.pendente, 403),
            ('napne aprovado', self.napne, 200),
        ]
        for rotulo, quem, esperado in casos:
            with self.subTest(perfil=rotulo):
                self.client.logout()
                if quem:
                    self.client.force_login(quem)
                resposta = self.client.get(self.url_detalhe())
                self.assertEqual(resposta.status_code, esperado)
                if rotulo == 'visitante':
                    self.assertIn('login', resposta.url)

    def test_somente_napne_aprovado_consegue_registrar_a_decisao(self):
        for rotulo, quem in [('visitante', None), ('estudante', self.estudante), ('professor', self.professor), ('pendente', self.pendente)]:
            with self.subTest(perfil=rotulo):
                self.client.logout()
                if quem:
                    self.client.force_login(quem)
                resposta = self.client.post(self.url_detalhe(), {'decisao': 'aprovar', 'parecer': ''})
                self.assertIn(resposta.status_code, (302, 403))
                self.pei.refresh_from_db()
                self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        self.assertFalse(HistoricoPei.objects.exists())
        self.assertFalse(Notificacao.objects.exists())

    def test_aprovar_sem_parecer(self):
        self.client.force_login(self.napne)
        resposta = self.client.post(self.url_detalhe(), {'decisao': 'aprovar', 'parecer': ''}, follow=True)

        self.assertEqual(resposta.status_code, 200)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.ANALISADO)
        self.assertContains(resposta, 'Análise registrada')
        self.assertEqual(Notificacao.objects.filter(destinatario=self.professor).count(), 1)

    def test_devolver_com_parecer_aparece_no_historico_da_tela(self):
        self.client.force_login(self.napne)
        self.client.post(self.url_detalhe(), {'decisao': 'devolver', 'parecer': 'Incluir metas por bimestre.'})

        resposta = self.client.get(self.url_detalhe())
        self.assertContains(resposta, 'Incluir metas por bimestre.')
        self.assertContains(resposta, 'PEI devolvido pelo NAPNE')
        self.assertContains(resposta, 'Napne1')  # autor
        self.assertContains(resposta, 'Aguardando nova versão do professor')
        self.assertNotContains(resposta, 'id="form-analise-pei"')

    def test_devolver_sem_parecer_mostra_o_erro_e_nao_altera_nada(self):
        self.client.force_login(self.napne)
        resposta = self.client.post(self.url_detalhe(), {'decisao': 'devolver', 'parecer': ''})

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'O parecer é obrigatório ao devolver ou solicitar ajustes.')
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        self.assertFalse(Notificacao.objects.exists())

    def test_enviar_sem_escolher_a_decisao(self):
        self.client.force_login(self.napne)
        resposta = self.client.post(self.url_detalhe(), {'parecer': 'x'})
        self.assertContains(resposta, 'Escolha uma decisão')
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)

    def test_nao_registra_decisao_em_pei_que_nao_esta_em_analise(self):
        Pei.objects.filter(pk=self.pei.pk).update(status=Pei.ANALISADO)
        self.client.force_login(self.napne)

        resposta = self.client.post(self.url_detalhe(), {'decisao': 'devolver', 'parecer': 'Tarde demais'}, follow=True)

        self.assertContains(resposta, 'Só é possível registrar decisão em PEI')
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.ANALISADO)
        self.assertFalse(HistoricoPei.objects.exists())
        self.assertFalse(Notificacao.objects.exists())

    def test_detalhe_mostra_o_formulario_so_quando_esta_em_analise(self):
        self.client.force_login(self.napne)
        self.assertContains(self.client.get(self.url_detalhe()), 'id="form-analise-pei"')

        Pei.objects.filter(pk=self.pei.pk).update(status=Pei.ANALISADO)
        resposta = self.client.get(self.url_detalhe())
        self.assertNotContains(resposta, 'id="form-analise-pei"')
        self.assertContains(resposta, 'Análise concluída')

    def test_detalhe_lista_as_versoes_com_download(self):
        self.client.force_login(self.napne)
        resposta = self.client.get(self.url_detalhe())
        versao = self.pei.versao_atual
        self.assertContains(resposta, reverse('baixar_versao_pei', args=[versao.id]))
        self.assertContains(resposta, 'atual')

    def test_selo_de_status_usa_classe_com_contraste(self):
        self.client.force_login(self.napne)
        resposta = self.client.get(self.url_detalhe())
        self.assertContains(resposta, 'badge text-bg-warning')
        self.assertNotContains(resposta, 'badge bg-warning')


class ListagemEEdicaoDePeisTests(BaseTestes):
    def setUp(self):
        super().setUp()
        self.devolvido = criar_pei(self.professor, titulo='PEI devolvido')
        self.devolvido.registrar_analise(Pei.DECISAO_DEVOLVER, 'Rever.', self.napne)
        self.client.force_login(self.napne)

    def test_listagem_mostra_status_e_versao(self):
        resposta = self.client.get(reverse('listar_peis'))
        self.assertContains(resposta, 'PEI de Matemática')
        self.assertContains(resposta, 'Devolvido')
        self.assertContains(resposta, 'Analisar')  # o que está em análise

    def test_filtro_por_status(self):
        resposta = self.client.get(reverse('listar_peis'), {'status': Pei.DEVOLVIDO})
        self.assertContains(resposta, 'PEI devolvido')
        self.assertNotContains(resposta, 'PEI de Matemática')

    def test_status_desconhecido_no_filtro_e_ignorado(self):
        resposta = self.client.get(reverse('listar_peis'), {'status': 'analizado'})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'PEI de Matemática')

    def test_listagem_e_exclusiva_do_napne(self):
        self.client.force_login(self.professor)
        self.assertEqual(self.client.get(reverse('listar_peis')).status_code, 403)

    def test_editar_so_altera_os_dados_e_nunca_o_arquivo(self):
        arquivo_antes = self.pei.arquivo.name
        resposta = self.client.post(
             reverse('editar_pei', args=[self.pei.id]),
            {
                'titulo': 'Novo título',
                'estudante_nome': 'Joana Pereira de Souza',
                'estudante_matricula': '20231012345678',
                'estudante_curso': 'Técnico em Informática',
                'periodo_letivo': '2026.1',
                'arquivo': arquivo_pdf('intruso.pdf', b'%PDF-1.4 intruso'),
            },
         )
        self.assertEqual(resposta.status_code, 302)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.titulo, 'Novo título')
        self.assertEqual(self.pei.arquivo.name, arquivo_antes)
        self.assertEqual(self.pei.versoes.count(), 1)

    def test_painel_home_mostra_quantos_aguardam_analise(self):
        resposta = self.client.get(reverse('painel_home'))
        self.assertEqual(resposta.context['total_peis_em_analise'], 1)
        self.assertContains(resposta, 'aguardando análise')


class DownloadsDoPainelTests(BaseTestes):
    def test_napne_baixa_a_versao_atual_com_nome_limpo(self):
        self.client.force_login(self.napne)
        resposta = self.client.get(reverse('baixar_pei', args=[self.pei.id]))
        self.assertEqual(resposta.status_code, 200)
        cabecalho = resposta['Content-Disposition']
        self.assertTrue(cabecalho.startswith('attachment'))
        self.assertNotIn('pei/', cabecalho)  # sem a pasta de armazenamento

    def test_napne_baixa_uma_versao_especifica(self):
        self.client.force_login(self.napne)
        resposta = self.client.get(reverse('baixar_versao_pei', args=[self.pei.versao_atual.id]))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(b''.join(resposta.streaming_content), b'%PDF-1.4 conteudo de teste')

    def test_outros_perfis_nao_baixam_pelo_painel(self):
        versao = self.pei.versao_atual
        for quem in (self.professor, self.estudante, self.pendente):
            self.client.force_login(quem)
            self.assertEqual(self.client.get(reverse('baixar_pei', args=[self.pei.id])).status_code, 403)
            self.assertEqual(self.client.get(reverse('baixar_versao_pei', args=[versao.id])).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('baixar_pei', args=[self.pei.id])).status_code, 302)

    def test_arquivo_ausente_no_disco_vira_404(self):
        self.pei.versao_atual.arquivo.delete(save=False)
        self.client.force_login(self.napne)
        resposta = self.client.get(reverse('baixar_versao_pei', args=[self.pei.versao_atual.id]))
        self.assertEqual(resposta.status_code, 404)


class TelasRemovidasTests(BaseTestes):
    def test_telas_de_historico_e_alterar_status_nao_existem_mais(self):
        for nome in ('listar_historico_peis', 'historico_meus_peis'):
            with self.assertRaises(NoReverseMatch):
                reverse(nome)
        with self.assertRaises(NoReverseMatch):
            reverse('alterar_status_pei', args=[self.pei.id])

        self.client.force_login(self.napne)
        self.assertEqual(self.client.get('/painel/historico-peis/').status_code, 404)
        self.assertEqual(self.client.get(f'/painel/pei/{self.pei.id}/alterar-status/').status_code, 404)
        self.client.force_login(self.professor)
        self.assertEqual(self.client.get('/meus-peis/historico/').status_code, 404)


class MigracaoDeDadosTests(BaseTestes):
    def test_corrige_o_valor_com_erro_de_digitacao_e_cria_a_versao_1(self):
        modulo = importlib.import_module('core.migrations.0012_dados_de_versoes_e_status')

        # Simula um banco antigo: valor "analizado", sem versões e histórico solto.
        Pei.objects.filter(pk=self.pei.pk).update(status='analizado')
        HistoricoPei.objects.create(pei=self.pei, status_anterior='em_analise', status_novo='analizado', alterado_por=self.napne)
        self.pei.versoes.all().delete()

        modulo.migrar_dados(apps, None)

        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, 'analisado')
        historico = self.pei.historico.get()
        self.assertEqual(historico.status_novo, 'analisado')
        versao = self.pei.versoes.get()
        self.assertEqual(versao.numero, 1)
        self.assertEqual(versao.arquivo.name, self.pei.arquivo.name)
        self.assertEqual(historico.versao, versao)

    def test_migracao_pode_rodar_duas_vezes_sem_duplicar(self):
        modulo = importlib.import_module('core.migrations.0012_dados_de_versoes_e_status')
        modulo.migrar_dados(apps, None)
        modulo.migrar_dados(apps, None)
        self.assertEqual(self.pei.versoes.count(), 1)
