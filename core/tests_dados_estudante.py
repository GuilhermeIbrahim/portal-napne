import importlib
import os
import re
from io import StringIO

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from .forms import EditarPeiForm, PeiForm
from .models import Notificacao, Pei, RegistroAcessoPei, VersaoPei
from .tests import BaseTestes, arquivo_pdf, criar_pei
from .validators import (
    normalizar_matricula,
    normalizar_periodo_letivo,
    titulo_revela_o_estudante,
    validar_curso,
    validar_matricula,
    validar_nome_estudante,
    validar_periodo_letivo,
)

DADOS = dict(
    estudante_nome='Joana Pereira de Souza',
    estudante_matricula='20231012345678',
    estudante_curso='Técnico em Informática',
    periodo_letivo='2026.1',
)
TITULO = 'PEI de Matemática - 7º ano'


def dados_do_formulario(**mudancas):
    dados = {'titulo': TITULO, **DADOS}
    dados.update(mudancas)
    return dados


def titulo_da_pagina(resposta):
    return re.search(r'<title>(.*?)</title>', resposta.content.decode(), re.S).group(1).strip()


def mensagens(erro):
    try:
        erro()
    except ValidationError as e:
        return e.messages
    return []


class PeiComEstudanteBase(BaseTestes):
    def setUp(self):
        super().setUp()
        self.pei = criar_pei(self.professor, titulo=TITULO, **DADOS)


# ---------------------------------------------------------------------------------------
class ValidadoresTests(BaseTestes):
    def test_nome_aceita_nomes_reais(self):
        for nome in ('João da Silva', "Maria D'Ávila-Souza Jr.", 'Ana Júlia Matos', 'José de Alencar'):
            self.assertEqual(mensagens(lambda: validar_nome_estudante(nome)), [], nome)

    def test_nome_recusa_um_so_nome_numeros_e_simbolos(self):
        for nome in ('João', 'João Silva 2', 'João <b>Silva</b>', '123 456', '', 'João;DROP TABLE'):
            self.assertTrue(mensagens(lambda: validar_nome_estudante(nome)), nome)

    def test_periodo_normaliza_varios_formatos_para_ano_ponto_semestre(self):
        casos = {'2026.1': '2026.1', '2026/1': '2026.1', '2026-2': '2026.2', ' 2026  1 ': '2026.1', '20261': '2026.1', 'abc': 'abc'}
        for entrada, esperado in casos.items():
            self.assertEqual(normalizar_periodo_letivo(entrada), esperado, entrada)

    def test_periodo_valida_semestre_e_faixa_de_anos(self):
        self.assertEqual(mensagens(lambda: validar_periodo_letivo('2026.1')), [])
        self.assertEqual(mensagens(lambda: validar_periodo_letivo('2026.2')), [])
        for ruim in ('2026.3', '2026.0', '1999.1', '2999.1', '26.1', '2026', 'abc', ''):
            self.assertTrue(mensagens(lambda: validar_periodo_letivo(ruim)), ruim)

    def test_matricula_guarda_so_numeros(self):
        self.assertEqual(normalizar_matricula('2024.1181-1100 04'), '20241181110004')
        
        def test_matricula_tem_exatamente_14_digitos(self):
            for boa in ('20241181110004', '2024.1181-1100 04', '20241181110004'):
                self.assertEqual(mensagens(lambda: validar_matricula(boa)), [], boa)
            for ruim in ('2024118111000', '2024.1181-1100 44A', '20241181110O04', '1'*21, '', 'abcdefghijklmn'):
                self.assertEqual(mensagens(lambda: validar_matricula(ruim)), [], ruim)
                

    def test_curso(self):
        self.assertEqual(mensagens(lambda: validar_curso('Técnico em Informática (Integrado)')), [])
        for ruim in ('12', '<script>', 'ab'):
            self.assertTrue(mensagens(lambda: validar_curso(ruim)), ruim)

    def test_titulo_nao_pode_revelar_o_estudante(self):
        nome, matricula = DADOS['estudante_nome'], DADOS['estudante_matricula']
        revelam = ['PEI de Joana', 'PEI do aluno SOUZA', 'pei da joana pereira', 'PEI 20231012345678', 'PEI 2023.1012.3456.78']
        for titulo in revelam:
            self.assertTrue(titulo_revela_o_estudante(titulo, nome, matricula), titulo)
        for titulo in (TITULO, 'Análise do PEI', 'PEI - Adaptações de avaliação', 'Plano de 2026'):
            self.assertFalse(titulo_revela_o_estudante(titulo, nome, matricula), titulo)

    def test_particulas_do_nome_nao_geram_falso_positivo(self):
        self.assertFalse(titulo_revela_o_estudante('PEI de Matemática', 'João da Silva'))
        self.assertFalse(titulo_revela_o_estudante('Plano de adaptação', 'Ana de Souza'))  # "ana" não é "adaptação"


# ---------------------------------------------------------------------------------------
class FormularioDeEnvioTests(BaseTestes):
    def form(self, **mudancas):
        return PeiForm(data=dados_do_formulario(**mudancas), files={'arquivo': arquivo_pdf()})

    def test_formulario_valido_normaliza_os_dados(self):
        form = self.form(
            estudante_nome='  Joana   Pereira  de Souza ',
            estudante_matricula='2023.1012-3456 78',
            periodo_letivo='2026/1',
            estudante_curso='  Técnico em   Informática ',
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['estudante_nome'], 'Joana Pereira de Souza')
        self.assertEqual(form.cleaned_data['estudante_matricula'], '20231012345678')
        self.assertEqual(form.cleaned_data['periodo_letivo'], '2026.1')
        self.assertEqual(form.cleaned_data['estudante_curso'], 'Técnico em Informática')

    def test_os_quatro_campos_sao_obrigatorios_com_mensagem_em_portugues(self):
        esperadas = {
            'estudante_nome': 'Informe o nome completo do estudante.',
            'estudante_matricula': 'Informe a matrícula do estudante.',
            'estudante_curso': 'Informe o curso do estudante.',
            'periodo_letivo': 'Informe o período letivo.',
        }
        for campo, mensagem in esperadas.items():
            with self.subTest(campo=campo):
                form = self.form(**{campo: ''})
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors[campo], [mensagem])

    def test_mensagens_de_formato_em_portugues(self):
        self.assertIn('ano.semestre', self.form(periodo_letivo='2026.3').errors['periodo_letivo'][0])
        self.assertIn('apenas números', self.form(estudante_matricula='abc12345').errors['estudante_matricula'][0])
        self.assertIn('nome completo', self.form(estudante_nome='Joana').errors['estudante_nome'][0])

    def test_titulo_com_nome_ou_matricula_do_estudante_e_recusado(self):
        for titulo in ('PEI de Joana Pereira', 'PEI 20231012345678'):
            form = self.form(titulo=titulo)
            self.assertFalse(form.is_valid(), titulo)
            self.assertIn('não deve conter o nome nem a matrícula', form.errors['titulo'][0])

    def test_ajuda_orienta_a_nao_escrever_dados_de_saude(self):
        form = self.form()
        self.assertIn('Não escreva diagnóstico, laudo', form.fields['estudante_nome'].help_text)
        self.assertIn('Não use o nome do estudante', form.fields['titulo'].help_text)

    def test_edicao_pelo_napne_valida_do_mesmo_jeito(self):
        pei = criar_pei(self.professor)
        form = EditarPeiForm(data=dados_do_formulario(periodo_letivo='2026.9'), instance=pei)
        self.assertFalse(form.is_valid())
        self.assertIn('periodo_letivo', form.errors)

    def test_envio_pela_tela_grava_os_dados(self):
        self.client.force_login(self.professor)
        resposta = self.client.post(reverse('enviar_pei'), {**dados_do_formulario(periodo_letivo='2026-2'), 'arquivo': arquivo_pdf()}, follow=True)
        self.assertRedirects(resposta, reverse('meus_peis'))
        pei = Pei.objects.get(titulo=TITULO)
        self.assertEqual((pei.estudante_nome, pei.estudante_matricula, pei.estudante_curso, pei.periodo_letivo),
                         (DADOS['estudante_nome'], DADOS['estudante_matricula'], DADOS['estudante_curso'], '2026.2'))
        self.assertNotIn(DADOS['estudante_nome'], resposta.content.decode().split('class="alert')[1].split('</div>')[0])  # mensagem de sucesso sem dados

    def test_envio_com_erro_nao_cria_pei_e_mostra_os_erros(self):
        self.client.force_login(self.professor)
        antes = Pei.objects.count()
        resposta = self.client.post(reverse('enviar_pei'), {**dados_do_formulario(estudante_matricula='12'), 'arquivo': arquivo_pdf()})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'apenas números')
        self.assertEqual(Pei.objects.count(), antes)

    def test_formulario_mostra_o_aviso_de_privacidade_e_o_link(self):
        self.client.force_login(self.professor)
        resposta = self.client.get(reverse('enviar_pei'))
        self.assertContains(resposta, 'Dados protegidos.')
        self.assertContains(resposta, reverse('privacidade'))
        for rotulo in ('Nome completo do estudante', 'Matrícula do estudante', 'Curso do estudante', 'Período letivo'):
            self.assertContains(resposta, rotulo)


# ---------------------------------------------------------------------------------------
class ExibicaoDosDadosTests(PeiComEstudanteBase):
    def test_detalhe_e_listagem_do_painel_mostram_os_dados(self):
        self.client.force_login(self.napne)
        detalhe = self.client.get(reverse('detalhar_pei', args=[self.pei.id]))
        for valor in DADOS.values():
            self.assertContains(detalhe, valor)
        listagem = self.client.get(reverse('listar_peis'))
        for valor in (DADOS['estudante_nome'], DADOS['estudante_matricula'], DADOS['periodo_letivo']):
            self.assertContains(listagem, valor)

    def test_professor_dono_ve_os_dados_na_lista_e_no_detalhe(self):
        self.client.force_login(self.professor)
        for url in (reverse('meus_peis'), reverse('detalhar_meu_pei', args=[self.pei.id])):
            resposta = self.client.get(url)
            self.assertContains(resposta, DADOS['estudante_nome'])
        self.assertContains(self.client.get(reverse('detalhar_meu_pei', args=[self.pei.id])), DADOS['estudante_matricula'])

    def test_pei_antigo_sem_os_dados_aparece_como_nao_informado(self):
        antigo = criar_pei(self.professor, titulo='PEI antigo')
        self.client.force_login(self.napne)
        resposta = self.client.get(reverse('detalhar_pei', args=[antigo.id]))
        self.assertContains(resposta, 'Não informado')
        self.assertEqual(self.client.get(reverse('listar_peis')).status_code, 200)

    def test_napne_completa_os_dados_de_pei_antigo_pela_edicao(self):
        antigo = criar_pei(self.professor, titulo='PEI antigo')
        self.client.force_login(self.napne)
        resposta = self.client.post(reverse('editar_pei', args=[antigo.id]), dados_do_formulario(titulo='PEI antigo'))
        self.assertEqual(resposta.status_code, 302)
        antigo.refresh_from_db()
        self.assertEqual(antigo.estudante_nome, DADOS['estudante_nome'])

    def test_filtro_por_periodo_letivo(self):
        criar_pei(self.professor, titulo='PEI de Física', **{**DADOS, 'periodo_letivo': '2025.2'})
        self.client.force_login(self.napne)
        resposta = self.client.get(reverse('listar_peis'), {'periodo': '2025.2'})
        self.assertContains(resposta, 'PEI de Física')
        self.assertNotContains(resposta, TITULO)

    def test_periodo_desconhecido_no_filtro_e_ignorado(self):
        self.client.force_login(self.napne)
        resposta = self.client.get(reverse('listar_peis'), {'periodo': '1900.1'})
        self.assertContains(resposta, TITULO)

    def test_nao_existe_busca_por_nome_ou_matricula_na_url(self):
        """Buscar por dado pessoal na URL o deixaria no histórico do navegador e nos logs."""
        outro = criar_pei(self.professor, titulo='PEI de Física', **{**DADOS, 'estudante_nome': 'Carlos Alberto Lima', 'estudante_matricula': '20199999999999'})
        self.client.force_login(self.napne)
        for parametro in ('q', 'busca', 'estudante', 'estudante_nome', 'matricula', 'estudante_matricula'):
            resposta = self.client.get(reverse('listar_peis'), {parametro: 'Carlos'})
            self.assertContains(resposta, outro.titulo, msg_prefix=parametro)  # o parâmetro não filtra nada
            self.assertContains(resposta, TITULO, msg_prefix=parametro)

    def test_dados_aparecem_no_admin(self):
        admin = get_user_model().objects.create_superuser('admin', 'a@a.com', 'x')
        self.client.force_login(admin)
        lista = self.client.get(reverse('admin:core_pei_changelist'))
        self.assertContains(lista, DADOS['estudante_nome'])
        self.assertContains(lista, DADOS['periodo_letivo'])
        form = self.client.get(reverse('admin:core_pei_change', args=[self.pei.id]))
        for valor in DADOS.values():
            self.assertContains(form, valor)

    def test_admin_nao_expoe_link_do_arquivo_e_nao_cria_pei(self):
        admin = get_user_model().objects.create_superuser('admin', 'a@a.com', 'x')
        self.client.force_login(admin)
        resposta = self.client.get(reverse('admin:core_pei_change', args=[self.pei.id]))
        self.assertEqual(resposta.status_code, 200)
        html = resposta.content.decode()
        self.assertNotIn(self.pei.arquivo.name, html)
        self.assertNotIn('/media/', html)
        self.assertContains(resposta, f'PEI-{self.pei.id}-v1.pdf (área privada)')
        self.assertEqual(self.client.get(reverse('admin:core_pei_add')).status_code, 403)

    def test_admin_nao_busca_por_dado_do_estudante(self):
        from django.contrib import admin as django_admin
        campos = django_admin.site._registry[Pei].search_fields
        self.assertEqual(tuple(campos), ('titulo',))


# ---------------------------------------------------------------------------------------
class AcessoRestritoAosDadosTests(PeiComEstudanteBase):
    def telas(self):
        pei = self.pei.id
        return {
            'detalhe do painel': reverse('detalhar_pei', args=[pei]),
            'listagem do painel': reverse('listar_peis'),
            'edição do painel': reverse('editar_pei', args=[pei]),
            'detalhe do professor': reverse('detalhar_meu_pei', args=[pei]),
            'listagem do professor': reverse('meus_peis'),
        }

    def test_so_o_professor_dono_e_o_napne_veem_os_dados(self):
        permitidos = {
            'detalhe do painel': {'napne'},
            'listagem do painel': {'napne'},
            'edição do painel': {'napne'},
            'detalhe do professor': {'dono'},
            'listagem do professor': {'dono'},
        }
        perfis = {
            'visitante': None, 'estudante': self.estudante, 'outro professor': self.outro_professor,
            'napne pendente': self.pendente, 'dono': self.professor, 'napne': self.napne,
        }
        for tela, url in self.telas().items():
            for perfil, quem in perfis.items():
                with self.subTest(tela=tela, perfil=perfil):
                    self.client.logout()
                    if quem:
                        self.client.force_login(quem)
                    resposta = self.client.get(url)
                    html = resposta.content.decode()
                    if perfil in permitidos[tela]:
                        self.assertEqual(resposta.status_code, 200)
                        self.assertIn(DADOS['estudante_nome'], html)
                    else:
                        # "Meus PEIs" de outro professor abre (é a lista dele), mas sem os dados deste PEI.
                        lista_propria = tela == 'listagem do professor' and perfil == 'outro professor'
                        self.assertIn(resposta.status_code, (200,) if lista_propria else (302, 403))
                        for valor in DADOS.values():
                            self.assertNotIn(valor, html)

    def test_lista_do_professor_nao_mostra_estudantes_de_outro_professor(self):
        criar_pei(self.outro_professor, titulo='PEI do colega', **{**DADOS, 'estudante_nome': 'Carlos Alberto Lima'})
        self.client.force_login(self.professor)
        html = self.client.get(reverse('meus_peis')).content.decode()
        self.assertNotIn('Carlos Alberto Lima', html)

    def test_admin_exige_conta_de_equipe(self):
        for quem in (None, self.professor, self.napne, self.estudante):
            self.client.logout()
            if quem:
                self.client.force_login(quem)
            resposta = self.client.get(reverse('admin:core_pei_changelist'))
            self.assertEqual(resposta.status_code, 302)
            for valor in DADOS.values():
                self.assertNotIn(valor, resposta.content.decode())


# ---------------------------------------------------------------------------------------
class DadosNaoVazamTests(PeiComEstudanteBase):
    """Nome, matrícula e curso não aparecem em notificações, URLs, títulos de página nem downloads."""

    def sensiveis(self):
        return [DADOS['estudante_nome'], 'Joana', 'Pereira', DADOS['estudante_matricula'], DADOS['estudante_curso'], TITULO]

    def decidir_tudo(self):
        self.pei.registrar_analise(Pei.DECISAO_AJUSTES, 'Ajustar a avaliação.', self.napne)
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf'), self.professor)
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Devolvendo.', self.napne)
        self.pei.enviar_nova_versao(arquivo_pdf('v3.pdf'), self.professor)
        self.pei.registrar_analise(Pei.DECISAO_APROVAR, '', self.napne)

    def test_notificacoes_nao_trazem_dados_do_estudante_nem_o_titulo(self):
        self.decidir_tudo()
        notificacoes = Notificacao.objects.all()
        self.assertEqual(notificacoes.count(), 3)
        for n in notificacoes:
            for valor in self.sensiveis():
                self.assertNotIn(valor, n.titulo)
                self.assertNotIn(valor, n.conteudo)
                self.assertNotIn(valor, n.link)
            self.assertIn(f'nº {self.pei.id}', n.titulo)

    def test_notificacao_nao_aparece_com_dados_na_lista_na_api_nem_no_detalhe(self):
        base = Notificacao.objects.create(titulo='Base', conteudo='x', destino_tipo=Notificacao.TODOS)
        self.decidir_tudo()
        self.client.force_login(self.professor)
        textos = [
            self.client.get(reverse('minhas_notificacoes')).content.decode(),
            self.client.get(reverse('api_notificacoes_novas'), {'desde': base.id, 'lista': '1'}).content.decode(),
        ]
        for n in Notificacao.objects.exclude(pk=base.pk):
            textos.append(self.client.get(reverse('detalhar_notificacao', args=[n.id])).content.decode())
        for texto in textos:
            for valor in self.sensiveis():
                self.assertNotIn(valor, texto)

    def test_napne_ve_notificacoes_sem_dados_na_listagem_do_painel(self):
        self.decidir_tudo()
        self.client.force_login(self.napne)
        html = self.client.get(reverse('listar_notificacoes')).content.decode()
        for valor in self.sensiveis():
            self.assertNotIn(valor, html)

    def test_urls_so_tem_numeros(self):
        self.decidir_tudo()
        urls = [
            reverse('detalhar_pei', args=[self.pei.id]), reverse('editar_pei', args=[self.pei.id]),
            reverse('baixar_pei', args=[self.pei.id]), reverse('listar_peis'),
            reverse('detalhar_meu_pei', args=[self.pei.id]), reverse('reenviar_pei', args=[self.pei.id]),
            reverse('meus_peis'), reverse('enviar_pei'),
        ] + [reverse('baixar_versao_pei', args=[v.id]) for v in self.pei.versoes.all()] \
          + [reverse('baixar_minha_versao_pei', args=[v.id]) for v in self.pei.versoes.all()] \
          + [n.link for n in Notificacao.objects.all()]
        for url in urls:
            for valor in self.sensiveis() + ['joana', 'pereira', 'matematica']:
                self.assertNotIn(valor.lower(), url.lower(), url)

    def test_redirecionamentos_nao_levam_dados_na_url(self):
        self.client.force_login(self.napne)
        resposta = self.client.post(reverse('detalhar_pei', args=[self.pei.id]), {'decisao': 'aprovar', 'parecer': ''})
        for valor in self.sensiveis():
            self.assertNotIn(valor, resposta.url)

    def test_titulo_da_aba_nunca_tem_dados_do_estudante_nem_o_titulo_do_pei(self):
        paginas = [
            (self.napne, reverse('detalhar_pei', args=[self.pei.id])),
            (self.napne, reverse('listar_peis')),
            (self.napne, reverse('editar_pei', args=[self.pei.id])),
            (self.professor, reverse('detalhar_meu_pei', args=[self.pei.id])),
            (self.professor, reverse('meus_peis')),
            (self.professor, reverse('enviar_pei')),
        ]
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'x', self.napne)
        paginas.append((self.professor, reverse('reenviar_pei', args=[self.pei.id])))
        for quem, url in paginas:
            self.client.force_login(quem)
            titulo = titulo_da_pagina(self.client.get(url))
            for valor in self.sensiveis():
                self.assertNotIn(valor, titulo, url)

    def test_titulo_da_aba_do_professor_usa_so_o_numero_do_pei(self):
        self.client.force_login(self.professor)
        self.assertEqual(titulo_da_pagina(self.client.get(reverse('detalhar_meu_pei', args=[self.pei.id]))),
                         f'PEI nº {self.pei.id} | Portal NAPNE')

    def test_nome_do_arquivo_original_nao_vai_para_o_servidor_nem_para_o_download(self):
        pei = Pei.objects.create(titulo='Outro PEI', arquivo=arquivo_pdf('PEI_Joana_Pereira_Souza.pdf'), professor=self.professor)
        self.assertRegex(pei.arquivo.name, r'^pei/[0-9a-f]{32}\.pdf$')
        self.assertNotIn('Joana', pei.arquivo.name)

        versao = pei.versao_atual
        self.assertEqual(versao.nome_do_download(), f'PEI-{pei.id}-v1.pdf')
        for quem, nome_da_url in ((self.napne, 'baixar_versao_pei'), (self.professor, 'baixar_minha_versao_pei')):
            self.client.force_login(quem)
            cabecalho = self.client.get(reverse(nome_da_url, args=[versao.id]))['Content-Disposition']
            self.assertIn(f'PEI-{pei.id}-v1.pdf', cabecalho)
            self.assertNotIn('Joana', cabecalho)
        self.client.force_login(self.napne)
        self.assertIn(f'PEI-{pei.id}-v1.pdf', self.client.get(reverse('baixar_pei', args=[pei.id]))['Content-Disposition'])

    def test_a_mensagem_de_sucesso_da_analise_nao_traz_dados_do_estudante(self):
        self.client.force_login(self.napne)
        resposta = self.client.post(reverse('detalhar_pei', args=[self.pei.id]), {'decisao': 'aprovar', 'parecer': ''}, follow=True)
        trecho = resposta.content.decode().split('Análise registrada')[1][:200]
        for valor in self.sensiveis():
            self.assertNotIn(valor, trecho)


# ---------------------------------------------------------------------------------------
class ArquivoPrivadoTests(PeiComEstudanteBase):
    def test_arquivo_fica_fora_da_pasta_publica_e_nao_tem_url(self):
        caminho = self.pei.arquivo.path
        publica = os.path.abspath(settings.MEDIA_ROOT)
        privada = os.path.abspath(settings.PEI_ARMAZENAMENTO_PRIVADO)

        self.assertTrue(os.path.isfile(caminho))
        self.assertTrue(caminho.startswith(privada + os.sep))
        self.assertFalse(caminho.startswith(publica + os.sep))
        self.assertFalse(privada.startswith(publica + os.sep))
        with self.assertRaises(ValueError):
            self.pei.arquivo.url
        with self.assertRaises(ValueError):
            self.pei.versao_atual.arquivo.url

    def test_nova_versao_tambem_vai_para_a_area_privada_com_nome_aleatorio(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'x', self.napne)
        self.pei.enviar_nova_versao(arquivo_pdf('Joana_corrigido.pdf'), self.professor)
        versao = self.pei.versao_atual
        self.assertRegex(versao.arquivo.name, r'^pei/[0-9a-f]{32}\.pdf$')
        self.assertTrue(versao.arquivo.path.startswith(os.path.abspath(settings.PEI_ARMAZENAMENTO_PRIVADO)))

    def test_os_templates_nunca_expoem_url_do_arquivo(self):
        self.client.force_login(self.napne)
        for url in (reverse('detalhar_pei', args=[self.pei.id]), reverse('listar_peis')):
            html = self.client.get(url).content.decode()
            self.assertNotIn(self.pei.arquivo.name, html)
            self.assertNotIn('/media/', html)


# ---------------------------------------------------------------------------------------
class EliminacaoDeArquivosTests(PeiComEstudanteBase):
    def test_excluir_o_pei_apaga_todos_os_arquivos_do_disco(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'x', self.napne)
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf'), self.professor)
        caminhos = [v.arquivo.path for v in self.pei.versoes.all()]
        self.assertEqual(len(caminhos), 2)
        self.assertTrue(all(os.path.isfile(c) for c in caminhos))

        self.client.force_login(self.napne)
        with self.captureOnCommitCallbacks(execute=True):
            resposta = self.client.post(reverse('excluir_pei', args=[self.pei.id]))

        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Pei.objects.filter(pk=self.pei.pk).exists())
        self.assertFalse(VersaoPei.objects.filter(pei_id=self.pei.pk).exists())
        for caminho in caminhos:
            self.assertFalse(os.path.exists(caminho), caminho)

    def test_arquivo_so_e_apagado_depois_do_commit(self):
        caminho = self.pei.arquivo.path
        with self.captureOnCommitCallbacks(execute=False):
            self.pei.delete()
        self.assertTrue(os.path.exists(caminho))  # a exclusão pode ser desfeita: o arquivo ainda está lá

    def test_nao_apaga_arquivo_que_ainda_e_usado_por_outro_registro(self):
        versao = self.pei.versao_atual
        caminho = versao.arquivo.path
        with self.captureOnCommitCallbacks(execute=True):
            versao.delete()  # o PEI ainda aponta para o mesmo arquivo
        self.assertTrue(os.path.exists(caminho))

    def test_o_historico_de_acessos_sobrevive_a_exclusao(self):
        self.client.force_login(self.napne)
        self.client.get(reverse('detalhar_pei', args=[self.pei.id]))
        pei_id = self.pei.id
        with self.captureOnCommitCallbacks(execute=True):
            self.pei.delete()
        self.assertTrue(RegistroAcessoPei.objects.filter(pei_id=pei_id).exists())


# ---------------------------------------------------------------------------------------
class RegistroDeAcessosTests(PeiComEstudanteBase):
    def acoes(self):
        return list(RegistroAcessoPei.objects.order_by('id').values_list('usuario__username', 'acao', 'versao_numero'))

    def test_napne_visualizar_o_detalhe_e_registrado(self):
        self.client.force_login(self.napne)
        self.client.get(reverse('detalhar_pei', args=[self.pei.id]))
        registro = RegistroAcessoPei.objects.get()
        self.assertEqual((registro.pei_id, registro.usuario, registro.acao), (self.pei.id, self.napne, RegistroAcessoPei.VISUALIZOU))
        self.assertIsNotNone(registro.criado_em)

    def test_downloads_do_napne_e_do_professor_sao_registrados_com_a_versao(self):
        versao = self.pei.versao_atual
        self.client.force_login(self.napne)
        self.client.get(reverse('baixar_pei', args=[self.pei.id]))
        self.client.get(reverse('baixar_versao_pei', args=[versao.id]))
        self.client.force_login(self.professor)
        self.client.get(reverse('baixar_minha_versao_pei', args=[versao.id]))
        self.assertEqual(self.acoes(), [('napne1', 'baixou', 1), ('napne1', 'baixou', 1), ('prof', 'baixou', 1)])

    def test_enviar_a_decisao_nao_gera_registro_de_visualizacao(self):
        self.client.force_login(self.napne)
        self.client.post(reverse('detalhar_pei', args=[self.pei.id]), {'decisao': 'aprovar', 'parecer': ''})
        self.assertEqual(RegistroAcessoPei.objects.count(), 0)

    def test_acessos_negados_nao_sao_registrados(self):
        versao = self.pei.versao_atual
        for quem in (self.estudante, self.outro_professor, self.pendente):
            self.client.force_login(quem)
            self.client.get(reverse('detalhar_pei', args=[self.pei.id]))
            self.client.get(reverse('baixar_versao_pei', args=[versao.id]))
            self.client.get(reverse('baixar_minha_versao_pei', args=[versao.id]))
        self.client.logout()
        self.client.get(reverse('baixar_pei', args=[self.pei.id]))
        self.assertEqual(RegistroAcessoPei.objects.count(), 0)

    def test_registro_nao_guarda_ip_nem_conteudo_do_pei(self):
        campos = {f.name for f in RegistroAcessoPei._meta.get_fields()}
        self.assertEqual(campos, {'id', 'pei_id', 'usuario', 'acao', 'versao_numero', 'criado_em'})

    def test_admin_mostra_o_registro_somente_leitura(self):
        RegistroAcessoPei.registrar(self.napne, self.pei, RegistroAcessoPei.VISUALIZOU)
        admin = get_user_model().objects.create_superuser('admin', 'a@a.com', 'x')
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse('admin:core_registroacessopei_changelist')), 'Visualizou o PEI')
        self.assertEqual(self.client.get(reverse('admin:core_registroacessopei_add')).status_code, 403)
        registro = RegistroAcessoPei.objects.get()
        self.assertEqual(self.client.post(reverse('admin:core_registroacessopei_delete', args=[registro.id]), {'post': 'yes'}).status_code, 403)
        self.assertTrue(RegistroAcessoPei.objects.exists())


# ---------------------------------------------------------------------------------------
class AvisoDePrivacidadeTests(BaseTestes):
    def test_pagina_e_publica_e_explica_o_tratamento(self):
        resposta = self.client.get(reverse('privacidade'))
        self.assertEqual(resposta.status_code, 200)
        for trecho in ('LGPD', 'dados pessoais sensíveis', 'Quem pode acessar', 'Seus direitos', 'matrícula', 'sem guardar endereço IP', 'também são apagados do servidor'):
            self.assertContains(resposta, trecho)

    def test_rodape_do_portal_leva_ao_aviso(self):
        self.assertContains(self.client.get(reverse('index')), reverse('privacidade'))


# ---------------------------------------------------------------------------------------
class ComandoDeArquivosOrfaosTests(PeiComEstudanteBase):
    def setUp(self):
        super().setUp()
        pasta = os.path.join(settings.PEI_ARMAZENAMENTO_PRIVADO, 'pei')
        publica = os.path.join(settings.MEDIA_ROOT, 'pei')
        os.makedirs(publica, exist_ok=True)
        self.orfao_privado = os.path.join(pasta, 'a' * 32 + '.pdf')
        self.orfao_publico = os.path.join(publica, 'PEI_Joana_antigo.pdf')
        for caminho in (self.orfao_privado, self.orfao_publico):
            with open(caminho, 'wb') as f:
                f.write(b'%PDF-1.4 orfao')

    def rodar(self, *args):
        saida = StringIO()
        call_command('apagar_arquivos_orfaos_pei', *args, stdout=saida)
        return saida.getvalue()

    def test_sem_apagar_so_lista(self):
        texto = self.rodar()
        self.assertIn(self.orfao_privado, texto)
        self.assertIn(self.orfao_publico, texto)
        self.assertTrue(os.path.exists(self.orfao_privado) and os.path.exists(self.orfao_publico))

    def test_com_apagar_remove_os_orfaos_e_preserva_os_arquivos_em_uso(self):
        em_uso = self.pei.arquivo.path
        self.rodar('--apagar')
        self.assertFalse(os.path.exists(self.orfao_privado))
        self.assertFalse(os.path.exists(self.orfao_publico))
        self.assertTrue(os.path.exists(em_uso))

    def test_sem_orfaos(self):
        self.rodar('--apagar')
        self.assertIn('Nenhum arquivo órfão', self.rodar())


# ---------------------------------------------------------------------------------------
class MigracaoDosArquivosParaAreaPrivadaTests(BaseTestes):
    def modulo(self):
        return importlib.import_module('core.migrations.0014_mover_arquivos_de_pei_para_area_privada')

    def colocar_arquivo_publico(self, nome, conteudo=b'%PDF-1.4 legado'):
        caminho = os.path.join(settings.MEDIA_ROOT, nome)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'wb') as f:
            f.write(conteudo)
        return caminho

    def test_move_o_arquivo_publico_para_a_area_privada_com_nome_aleatorio(self):
        publico = self.colocar_arquivo_publico('pei/PEI_Joana_Silva.pdf')
        Pei.objects.filter(pk=self.pei.pk).update(arquivo='pei/PEI_Joana_Silva.pdf')
        VersaoPei.objects.filter(pei=self.pei).update(arquivo='pei/PEI_Joana_Silva.pdf')

        self.modulo().mover_para_area_privada(apps, None)

        self.pei.refresh_from_db()
        novo = self.pei.arquivo.name
        self.assertRegex(novo, r'^pei/[0-9a-f]{32}\.pdf$')
        self.assertEqual(self.pei.versao_atual.arquivo.name, novo)  # PEI e versão continuam apontando para o mesmo arquivo
        self.assertFalse(os.path.exists(publico))
        with open(self.pei.arquivo.path, 'rb') as f:
            self.assertEqual(f.read(), b'%PDF-1.4 legado')

    def test_pode_rodar_duas_vezes(self):
        self.colocar_arquivo_publico('pei/legado.pdf')
        Pei.objects.filter(pk=self.pei.pk).update(arquivo='pei/legado.pdf')
        VersaoPei.objects.filter(pei=self.pei).update(arquivo='pei/legado.pdf')
        self.modulo().mover_para_area_privada(apps, None)
        self.pei.refresh_from_db()
        depois_da_primeira = self.pei.arquivo.name
        self.modulo().mover_para_area_privada(apps, None)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.arquivo.name, depois_da_primeira)
        self.assertTrue(os.path.exists(self.pei.arquivo.path))

    def test_registro_sem_arquivo_no_disco_e_deixado_como_esta(self):
        Pei.objects.filter(pk=self.pei.pk).update(arquivo='pei/sumiu.pdf')
        self.modulo().mover_para_area_privada(apps, None)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.arquivo.name, 'pei/sumiu.pdf')

    def test_nome_com_caminho_perigoso_nao_move_arquivos_de_fora_da_pasta_publica(self):
        fora = os.path.join(os.path.dirname(os.path.abspath(settings.MEDIA_ROOT)), 'fora-da-midia.txt')
        with open(fora, 'w') as f:
            f.write('nao mexa')
        self.addCleanup(lambda: os.path.exists(fora) and os.remove(fora))
        Pei.objects.filter(pk=self.pei.pk).update(arquivo='../fora-da-midia.txt')
        self.modulo().mover_para_area_privada(apps, None)
        self.assertTrue(os.path.exists(fora))
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.arquivo.name, '../fora-da-midia.txt')

    def test_os_dados_do_estudante_dos_peis_antigos_ficam_em_branco(self):
        antigo = criar_pei(self.professor, titulo='PEI de antes dos campos novos')
        antigo.refresh_from_db()
        self.assertEqual((antigo.estudante_nome, antigo.estudante_matricula, antigo.estudante_curso, antigo.periodo_letivo), ('', '', '', ''))
