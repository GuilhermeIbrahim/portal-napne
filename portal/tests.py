from django.urls import reverse

from core.models import Notificacao, Pei
from core.tests import BaseTestes, arquivo_pdf, criar_pei


class EnvioEAcompanhamentoDoProfessorTests(BaseTestes):
    def test_enviar_pei_leva_para_meus_peis_e_cria_a_versao_1(self):
        self.client.force_login(self.professor)
        resposta = self.client.post(
            reverse('enviar_pei'),
            {
                'titulo': 'PEI de História',
                'estudante_nome': 'Joana Pereira de Souza',
                'estudante_matricula': '20231012345678',
                'estudante_curso': 'Técnico em Informática',
                'periodo_letivo': '2026.1',
                'arquivo': arquivo_pdf('historia.pdf'),
            },
            follow=True,
        )
        self.assertRedirects(resposta, reverse('meus_peis'))
        self.assertContains(resposta, 'PEI enviado com sucesso')
        pei = Pei.objects.get(titulo='PEI de História')
        self.assertEqual(pei.professor, self.professor)
        self.assertEqual(pei.versoes.get().numero, 1)

    def test_meus_peis_mostra_so_os_do_professor_com_status_legivel(self):
        criar_pei(self.outro_professor, titulo='PEI do colega')
        self.client.force_login(self.professor)
        resposta = self.client.get(reverse('meus_peis'))
        self.assertContains(resposta, 'PEI de Matemática')
        self.assertNotContains(resposta, 'PEI do colega')
        self.assertContains(resposta, 'badge text-bg-warning')
        self.assertNotContains(resposta, 'badge bg-warning')

    def test_meus_peis_destaca_a_acao_necessaria_quando_devolvido(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Corrigir.', self.napne)
        self.client.force_login(self.professor)
        resposta = self.client.get(reverse('meus_peis'))
        self.assertContains(resposta, 'Ação necessária')
        self.assertContains(resposta, reverse('reenviar_pei', args=[self.pei.id]))

    def test_meus_peis_nao_oferece_reenvio_quando_em_analise(self):
        self.client.force_login(self.professor)
        self.assertNotContains(self.client.get(reverse('meus_peis')), reverse('reenviar_pei', args=[self.pei.id]))


class DetalheDoPeiParaOProfessorTests(BaseTestes):
    def url(self):
        return reverse('detalhar_meu_pei', args=[self.pei.id])

    def test_matriz_de_acesso(self):
        casos = [
            ('visitante', None, 302),
            ('estudante', self.estudante, 403),
            ('napne sem perfil de professor', self.napne, 403),
            ('outro professor', self.outro_professor, 403),
            ('professor dono', self.professor, 200),
        ]
        for rotulo, quem, esperado in casos:
            with self.subTest(perfil=rotulo):
                self.client.logout()
                if quem:
                    self.client.force_login(quem)
                self.assertEqual(self.client.get(self.url()).status_code, esperado)

    def test_professor_le_o_parecer_quando_devolvido(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Detalhar as metas do 1º bimestre.', self.napne)
        self.client.force_login(self.professor)
        resposta = self.client.get(self.url())
        self.assertContains(resposta, 'O NAPNE devolveu este PEI')
        self.assertContains(resposta, 'Detalhar as metas do 1º bimestre.')
        self.assertContains(resposta, reverse('reenviar_pei', args=[self.pei.id]))

    def test_professor_le_o_parecer_quando_ha_ajustes_solicitados(self):
        self.pei.registrar_analise(Pei.DECISAO_AJUSTES, 'Ajustar a seção de avaliação.', self.napne)
        self.client.force_login(self.professor)
        resposta = self.client.get(self.url())
        self.assertContains(resposta, 'solicitou ajustes neste PEI')
        self.assertContains(resposta, 'Ajustar a seção de avaliação.')

    def test_pei_analisado_mostra_conclusao_e_nao_oferece_reenvio(self):
        self.pei.registrar_analise(Pei.DECISAO_APROVAR, 'Tudo certo.', self.napne)
        self.client.force_login(self.professor)
        resposta = self.client.get(self.url())
        self.assertContains(resposta, 'Análise concluída')
        self.assertContains(resposta, 'Tudo certo.')
        self.assertNotContains(resposta, reverse('reenviar_pei', args=[self.pei.id]))

    def test_pei_em_analise_avisa_que_aguarda_decisao(self):
        self.client.force_login(self.professor)
        self.assertContains(self.client.get(self.url()), 'em análise pelo NAPNE')

    def test_professor_ve_historico_e_baixa_cada_versao(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Corrigir.', self.napne)
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf', b'%PDF-1.4 v2'), self.professor, 'Corrigido.')
        self.client.force_login(self.professor)

        resposta = self.client.get(self.url())

        for versao in self.pei.versoes.all():
            self.assertContains(resposta, reverse('baixar_minha_versao_pei', args=[versao.id]))
        self.assertContains(resposta, 'PEI devolvido pelo NAPNE')
        self.assertContains(resposta, 'Nova versão enviada pelo professor')
        self.assertContains(resposta, 'Corrigido.')


class ReenvioDeNovaVersaoTests(BaseTestes):
    def url(self):
        return reverse('reenviar_pei', args=[self.pei.id])

    def devolver(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Corrija o item 3.', self.napne)

    def test_formulario_mostra_o_parecer_para_orientar_a_correcao(self):
        self.devolver()
        self.client.force_login(self.professor)
        resposta = self.client.get(self.url())
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Corrija o item 3.')

    def test_envio_cria_a_versao_e_devolve_o_pei_para_analise(self):
        self.devolver()
        self.client.force_login(self.professor)
        resposta = self.client.post(
            self.url(),
            {'arquivo': arquivo_pdf('v2.pdf', b'%PDF-1.4 v2'), 'comentario': 'Item 3 corrigido.'},
            follow=True,
        )
        self.assertRedirects(resposta, reverse('detalhar_meu_pei', args=[self.pei.id]))
        self.assertContains(resposta, 'Nova versão enviada')

        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        self.assertEqual(self.pei.versoes.count(), 2)
        self.assertEqual(self.pei.historico.last().observacao, 'Item 3 corrigido.')

    def test_envio_sem_arquivo_mostra_o_erro(self):
        self.devolver()
        self.client.force_login(self.professor)
        resposta = self.client.post(self.url(), {'comentario': 'sem arquivo'})
        self.assertContains(resposta, 'Selecione o arquivo corrigido do PEI.')
        self.assertEqual(self.pei.versoes.count(), 1)

    def test_nao_ha_reenvio_quando_o_pei_nao_foi_devolvido(self):
        self.client.force_login(self.professor)
        for status in (Pei.EM_ANALISE, Pei.ANALISADO):
            Pei.objects.filter(pk=self.pei.pk).update(status=status)
            resposta = self.client.post(self.url(), {'arquivo': arquivo_pdf('v2.pdf')}, follow=True)
            self.assertContains(resposta, 'Só é possível enviar uma nova versão')
        self.assertEqual(self.pei.versoes.count(), 1)

    def test_somente_o_professor_dono_envia(self):
        self.devolver()
        casos = [(None, 302), (self.estudante, 403), (self.napne, 403), (self.outro_professor, 403)]
        for quem, esperado in casos:
            self.client.logout()
            if quem:
                self.client.force_login(quem)
            resposta = self.client.post(self.url(), {'arquivo': arquivo_pdf('v2.pdf')})
            self.assertEqual(resposta.status_code, esperado, quem)
        self.assertEqual(self.pei.versoes.count(), 1)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.DEVOLVIDO)


class DownloadDasVersoesDoProfessorTests(BaseTestes):
    def test_dono_baixa_e_os_outros_nao(self):
        versao = self.pei.versao_atual
        url = reverse('baixar_minha_versao_pei', args=[versao.id])

        self.client.force_login(self.professor)
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(b''.join(resposta.streaming_content), b'%PDF-1.4 conteudo de teste')

        for quem, esperado in [(self.outro_professor, 403), (self.estudante, 403), (self.napne, 403)]:
            self.client.force_login(quem)
            self.assertEqual(self.client.get(url).status_code, esperado)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_versao_antiga_continua_baixavel_apos_nova_versao(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'x', self.napne)
        self.pei.enviar_nova_versao(arquivo_pdf('v2.pdf', b'%PDF-1.4 v2'), self.professor)
        primeira = self.pei.versoes.get(numero=1)
        self.client.force_login(self.professor)
        resposta = self.client.get(reverse('baixar_minha_versao_pei', args=[primeira.id]))
        self.assertEqual(b''.join(resposta.streaming_content), b'%PDF-1.4 conteudo de teste')


class NotificacaoDaAnaliseTests(BaseTestes):
    def test_professor_recebe_a_notificacao_com_botao_para_abrir_o_pei(self):
        self.pei.registrar_analise(Pei.DECISAO_AJUSTES, 'Parecer sigiloso.', self.napne)
        notificacao = Notificacao.objects.get()
        self.client.force_login(self.professor)

        lista = self.client.get(reverse('minhas_notificacoes'))
        self.assertContains(lista, 'Ajustes solicitados no PEI')

        detalhe = self.client.get(reverse('detalhar_notificacao', args=[notificacao.id]))
        self.assertContains(detalhe, f'href="{reverse("detalhar_meu_pei", args=[self.pei.id])}"')
        self.assertContains(detalhe, 'Abrir')
        self.assertNotContains(detalhe, 'Parecer sigiloso.')

    def test_api_ao_vivo_entrega_a_notificacao_ao_professor_e_a_mais_ninguem(self):
        base = Notificacao.objects.create(titulo='Base', conteudo='x', destino_tipo=Notificacao.TODOS)
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'x', self.napne)

        self.client.force_login(self.professor)
        dados = self.client.get(reverse('api_notificacoes_novas'), {'desde': base.id}).json()
        self.assertEqual([n['titulo'] for n in dados['novas']], [f'PEI devolvido (nº {self.pei.id})'])

        self.client.force_login(self.outro_professor)
        outros = self.client.get(reverse('api_notificacoes_novas'), {'desde': base.id}).json()
        self.assertEqual(outros['novas'], [])


class PaginaDeAcessoNegadoTests(BaseTestes):
    def test_professor_barrado_ve_a_pagina_do_portal_e_nao_o_layout_do_painel(self):
        self.client.force_login(self.professor)
        resposta = self.client.get(reverse('listar_peis'))
        self.assertEqual(resposta.status_code, 403)
        self.assertContains(resposta, 'Acesso restrito', status_code=403)
        self.assertContains(resposta, 'navbar-napne', status_code=403)      # layout do portal
        self.assertNotContains(resposta, 'app-sidebar', status_code=403)    # sem o menu do painel
