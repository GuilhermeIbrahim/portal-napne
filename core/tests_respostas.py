from unittest import mock

from django.db import IntegrityError, transaction
from django.urls import reverse

from .models import FeedbackPrivado, FeedbackPublico, Noticia, Notificacao, RespostaFeedback
from .tests import BaseTestes, MEDIA_TESTE, PRIVADO_TESTE, HASH_RAPIDO
from django.test import override_settings

SENHA = 'senha-forte-123'
TIPOS = ('publico', 'privado')


@override_settings(MEDIA_ROOT=MEDIA_TESTE, PEI_ARMAZENAMENTO_PRIVADO=PRIVADO_TESTE, PASSWORD_HASHERS=HASH_RAPIDO)
class BaseRespostas(BaseTestes):
    def setUp(self):
        super().setUp()
        self.noticia = Noticia.objects.create(titulo='Semana da Inclusão', conteudo='<p>Texto</p>')
        self.publico = FeedbackPublico.objects.create(noticia=self.noticia, conteudo='Comentário público', autor=self.estudante)
        self.privado = FeedbackPrivado.objects.create(noticia=self.noticia, conteudo='Mensagem privada', autor=self.estudante)

    def entrar(self, usuario):
        self.client.logout()
        self.client.login(username=usuario.username, password=SENHA)

    def feedback(self, tipo):
        return self.publico if tipo == 'publico' else self.privado

    def url_responder(self, tipo):
        return reverse(f'responder_feedback_{tipo}', args=[self.feedback(tipo).id])

    def responder(self, tipo, texto='Obrigado pelo retorno, vamos analisar.'):
        return self.client.post(self.url_responder(tipo), {'conteudo': texto})

    def resposta_de(self, tipo):
        feedback = self.feedback(tipo)
        feedback.refresh_from_db()
        return getattr(feedback, 'resposta', None)


class ModeloDaRespostaTests(BaseRespostas):
    def test_resposta_precisa_de_exatamente_um_feedback(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RespostaFeedback.objects.create(autor=self.napne, conteudo='sem feedback')
        with self.assertRaises(IntegrityError), transaction.atomic():
            RespostaFeedback.objects.create(
                autor=self.napne, conteudo='dois feedbacks',
                feedback_publico=self.publico, feedback_privado=self.privado,
            )

    def test_cada_feedback_tem_no_maximo_uma_resposta(self):
        RespostaFeedback.objects.create(autor=self.napne, conteudo='primeira', feedback_publico=self.publico)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RespostaFeedback.objects.create(autor=self.napne, conteudo='segunda', feedback_publico=self.publico)

    def test_apagar_o_feedback_apaga_a_resposta(self):
        RespostaFeedback.objects.create(autor=self.napne, conteudo='primeira', feedback_privado=self.privado)
        self.privado.delete()
        self.assertEqual(RespostaFeedback.objects.count(), 0)


class AcessoARespostaTests(BaseRespostas):
    def test_anonimo_vai_para_o_login(self):
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                resposta = self.client.get(self.url_responder(tipo))
                self.assertEqual(resposta.status_code, 302)
                self.assertIn('login', resposta.url)

    def test_quem_nao_e_do_napne_recebe_acesso_negado_e_nada_e_criado(self):
        for quem in (self.estudante, self.professor, self.pendente):
            self.entrar(quem)
            for tipo in TIPOS:
                with self.subTest(usuario=quem.username, tipo=tipo):
                    self.assertEqual(self.client.get(self.url_responder(tipo)).status_code, 403)
                    self.assertEqual(self.responder(tipo).status_code, 403)
        self.assertEqual(RespostaFeedback.objects.count(), 0)
        self.assertEqual(Notificacao.objects.count(), 0)

    def test_feedback_inexistente_da_404(self):
        self.entrar(self.napne)
        self.assertEqual(self.client.get(reverse('responder_feedback_publico', args=[9999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('responder_feedback_privado', args=[9999])).status_code, 404)


class CriarRespostaTests(BaseRespostas):
    def test_napne_ve_o_formulario_com_o_feedback_original(self):
        self.entrar(self.napne)
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                resposta = self.client.get(self.url_responder(tipo))
                self.assertEqual(resposta.status_code, 200)
                self.assertContains(resposta, self.feedback(tipo).conteudo)
                self.assertContains(resposta, 'Enviar resposta')

    def test_responder_cria_a_resposta_e_notifica_o_autor(self):
        self.entrar(self.napne)
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                antes = Notificacao.objects.count()
                resposta = self.responder(tipo, '  Obrigado pelo retorno.  ')
                self.assertRedirects(resposta, reverse(f'listar_feedbacks_{tipo}s'))

                criada = self.resposta_de(tipo)
                self.assertEqual(criada.conteudo, 'Obrigado pelo retorno.')
                self.assertEqual(criada.autor, self.napne)
                self.assertIsNotNone(criada.criado_em)
                self.assertIsNone(criada.editado_em)

                self.assertEqual(Notificacao.objects.count(), antes + 1)
                notificacao = Notificacao.objects.latest('id')
                self.assertEqual(notificacao.destino_tipo, Notificacao.USUARIO)
                self.assertEqual(notificacao.destinatario, self.estudante)
                self.assertEqual(notificacao.remetente, self.napne)
                self.assertEqual(notificacao.link, reverse(f'detalhar_feedback_{tipo}', args=[self.feedback(tipo).id]))
                self.assertIn('Obrigado pelo retorno.', notificacao.conteudo)
                self.assertTrue(notificacao.visivel_para(self.estudante))
                self.assertFalse(notificacao.visivel_para(self.professor))

    def test_resposta_vazia_ou_so_espacos_e_recusada(self):
        self.entrar(self.napne)
        for tipo in TIPOS:
            for texto in ('', '    '):
                with self.subTest(tipo=tipo, texto=texto):
                    resposta = self.responder(tipo, texto)
                    self.assertEqual(resposta.status_code, 200)
                    self.assertContains(resposta, 'Escreva a resposta')
        self.assertEqual(RespostaFeedback.objects.count(), 0)
        self.assertEqual(Notificacao.objects.count(), 0)

    def test_resposta_maior_que_500_caracteres_e_recusada(self):
        self.entrar(self.napne)
        resposta = self.responder('publico', 'a' * 501)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(RespostaFeedback.objects.count(), 0)

    def test_se_a_notificacao_falhar_a_resposta_tambem_nao_e_salva(self):
        self.entrar(self.napne)
        with mock.patch('core.views.Notificacao.objects.create', side_effect=RuntimeError('falhou')):
            with self.assertRaises(RuntimeError):
                self.responder('publico')
        self.assertEqual(RespostaFeedback.objects.count(), 0)
        self.assertEqual(Notificacao.objects.count(), 0)

    def test_responder_de_novo_edita_sem_criar_segunda_resposta_nem_nova_notificacao(self):
        self.entrar(self.napne)
        self.responder('publico', 'Primeira resposta')
        notificacoes = Notificacao.objects.count()

        self.responder('publico', 'Resposta corrigida')

        self.assertEqual(RespostaFeedback.objects.count(), 1)
        self.assertEqual(Notificacao.objects.count(), notificacoes)


class EditarEExcluirRespostaTests(BaseRespostas):
    def setUp(self):
        super().setUp()
        self.entrar(self.napne)
        for tipo in TIPOS:
            self.responder(tipo, 'Resposta inicial')

    def test_formulario_de_edicao_vem_preenchido(self):
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                resposta = self.client.get(self.url_responder(tipo))
                self.assertContains(resposta, 'Resposta inicial')
                self.assertContains(resposta, 'Salvar alterações')

    def test_editar_atualiza_o_texto_e_marca_editado_em(self):
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                self.responder(tipo, 'Texto novo')
                resposta = self.resposta_de(tipo)
                self.assertEqual(resposta.conteudo, 'Texto novo')
                self.assertIsNotNone(resposta.editado_em)

    def test_excluir_pede_confirmacao_e_so_apaga_no_post(self):
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                resposta = self.resposta_de(tipo)
                url = reverse('excluir_resposta_feedback', args=[resposta.id])

                pagina = self.client.get(url)
                self.assertEqual(pagina.status_code, 200)
                self.assertTrue(RespostaFeedback.objects.filter(id=resposta.id).exists())

                self.assertRedirects(self.client.post(url), reverse(f'listar_feedbacks_{tipo}s'))
                self.assertFalse(RespostaFeedback.objects.filter(id=resposta.id).exists())
                self.assertIsNone(self.resposta_de(tipo))

    def test_so_o_napne_exclui(self):
        resposta = self.resposta_de('publico')
        url = reverse('excluir_resposta_feedback', args=[resposta.id])
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)
        for quem in (self.estudante, self.professor):
            self.entrar(quem)
            self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(RespostaFeedback.objects.filter(id=resposta.id).exists())

    def test_so_o_napne_edita(self):
        self.entrar(self.estudante)
        self.assertEqual(self.responder('publico', 'Invasão').status_code, 403)
        self.assertEqual(self.resposta_de('publico').conteudo, 'Resposta inicial')


class SituacaoNasListasTests(BaseRespostas):
    def setUp(self):
        super().setUp()
        self.outro_publico = FeedbackPublico.objects.create(noticia=self.noticia, conteudo='Comentário sem resposta', autor=self.estudante)
        self.entrar(self.napne)
        self.responder('publico', 'Resposta ao primeiro')

    def test_lista_mostra_respondido_e_sem_resposta(self):
        resposta = self.client.get(reverse('listar_feedbacks_publicos'))
        self.assertContains(resposta, 'badge text-bg-success')
        self.assertContains(resposta, 'badge text-bg-warning')
        self.assertContains(resposta, 'Editar resposta')
        self.assertContains(resposta, 'Responder')

    def test_filtro_sem_resposta(self):
        resposta = self.client.get(reverse('listar_feedbacks_publicos'), {'status': 'sem_resposta'})
        self.assertEqual([f.id for f in resposta.context['feedbacks']], [self.outro_publico.id])

    def test_filtro_respondido(self):
        resposta = self.client.get(reverse('listar_feedbacks_publicos'), {'status': 'respondido'})
        self.assertEqual([f.id for f in resposta.context['feedbacks']], [self.publico.id])

    def test_filtro_invalido_mostra_todos(self):
        resposta = self.client.get(reverse('listar_feedbacks_publicos'), {'status': 'qualquer'})
        self.assertEqual(len(resposta.context['feedbacks']), 2)

    def test_filtro_tambem_existe_na_lista_privada(self):
        resposta = self.client.get(reverse('listar_feedbacks_privados'), {'status': 'respondido'})
        self.assertEqual(len(resposta.context['feedbacks']), 0)
        resposta = self.client.get(reverse('listar_feedbacks_privados'), {'status': 'sem_resposta'})
        self.assertEqual([f.id for f in resposta.context['feedbacks']], [self.privado.id])


class VisibilidadeDaRespostaTests(BaseRespostas):
    def setUp(self):
        super().setUp()
        self.entrar(self.napne)
        self.responder('publico', 'Resposta-publica-unica')
        self.responder('privado', 'Resposta-privada-unica')
        self.client.logout()

    def test_resposta_publica_aparece_na_pagina_da_noticia_para_qualquer_visitante(self):
        resposta = self.client.get(reverse('detalhe', args=[self.noticia.id]))
        self.assertContains(resposta, 'Resposta-publica-unica')

    def test_resposta_privada_nunca_aparece_na_pagina_da_noticia(self):
        resposta = self.client.get(reverse('detalhe', args=[self.noticia.id]))
        self.assertNotContains(resposta, 'Resposta-privada-unica')

    def test_autor_ve_a_resposta_nos_proprios_feedbacks(self):
        self.entrar(self.estudante)
        publica = self.client.get(reverse('detalhar_feedback_publico', args=[self.publico.id]))
        privada = self.client.get(reverse('detalhar_feedback_privado', args=[self.privado.id]))
        self.assertContains(publica, 'Resposta-publica-unica')
        self.assertContains(privada, 'Resposta-privada-unica')

    def test_outro_usuario_nao_ve_a_resposta_privada(self):
        self.entrar(self.professor)
        resposta = self.client.get(reverse('detalhar_feedback_privado', args=[self.privado.id]))
        self.assertEqual(resposta.status_code, 302)
        self.assertNotContains(self.client.get(reverse('index')), 'Resposta-privada-unica')

    def test_detalhe_sem_resposta_avisa_o_autor(self):
        novo = FeedbackPrivado.objects.create(noticia=self.noticia, conteudo='Outra mensagem', autor=self.estudante)
        self.entrar(self.estudante)
        resposta = self.client.get(reverse('detalhar_feedback_privado', args=[novo.id]))
        self.assertContains(resposta, 'Ainda sem resposta do NAPNE.')

    def test_botao_de_responder_so_aparece_para_o_napne(self):
        url = reverse('detalhar_feedback_publico', args=[self.publico.id])
        self.entrar(self.napne)
        self.assertContains(self.client.get(url), reverse('responder_feedback_publico', args=[self.publico.id]))
        self.entrar(self.estudante)
        self.assertNotContains(self.client.get(url), reverse('responder_feedback_publico', args=[self.publico.id]))
