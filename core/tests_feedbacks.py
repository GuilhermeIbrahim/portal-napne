from datetime import datetime

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from .models import FeedbackPrivado, FeedbackPublico, Noticia
from .tests import HASH_RAPIDO, BaseTestes, MEDIA_TESTE, PRIVADO_TESTE

SENHA = 'senha-forte-123'


def momento(dia, hora=12, minuto=0):
    return timezone.make_aware(datetime(2026, 11, dia, hora, minuto))


@override_settings(MEDIA_ROOT=MEDIA_TESTE, PEI_ARMAZENAMENTO_PRIVADO=PRIVADO_TESTE, PASSWORD_HASHERS=HASH_RAPIDO)
class BaseFeedbacks(BaseTestes):
    def setUp(self):
        super().setUp()
        self.noticia = Noticia.objects.create(titulo='Semana da Inclusão', conteudo='<p>Texto</p>')

    def entrar(self, usuario):
        self.client.login(username=usuario.username, password=SENHA)

    def publico(self, conteudo='Gostei da notícia', quando=None, autor=None, noticia='padrao'):
        feedback = FeedbackPublico.objects.create(
            noticia=self.noticia if noticia == 'padrao' else noticia,
            conteudo=conteudo,
            autor=autor or self.estudante,
        )
        if quando:
            FeedbackPublico.objects.filter(pk=feedback.pk).update(data=quando)
            feedback.refresh_from_db()
        return feedback

    def privado(self, conteudo='Preciso de ajuda', quando=None, autor=None, noticia='padrao'):
        feedback = FeedbackPrivado.objects.create(
            noticia=self.noticia if noticia == 'padrao' else noticia,
            conteudo=conteudo,
            autor=autor or self.estudante,
        )
        if quando:
            FeedbackPrivado.objects.filter(pk=feedback.pk).update(data=quando)
            feedback.refresh_from_db()
        return feedback


class DataEHoraDosFeedbacksTests(BaseFeedbacks):
    def test_o_feedback_guarda_data_e_hora(self):
        for criar in (self.publico, self.privado):
            with self.subTest(criar=criar.__name__):
                feedback = criar()
                self.assertIsInstance(feedback.data, datetime)
                self.assertIsNotNone(feedback.data.tzinfo)


class OrdenacaoDosFeedbacksTests(BaseFeedbacks):
    def ids_da_pagina(self, rota):
        resposta = self.client.get(reverse(rota))
        self.assertEqual(resposta.status_code, 200)
        return [f.id for f in resposta.context['feedbacks']]

    def test_publicos_do_mais_recente_para_o_mais_antigo(self):
        antigo = self.publico('antigo', momento(10, 9))
        recente = self.publico('recente', momento(20, 18))
        meio = self.publico('meio', momento(15, 12))
        self.entrar(self.napne)
        self.assertEqual(self.ids_da_pagina('listar_feedbacks_publicos'), [recente.id, meio.id, antigo.id])

    def test_privados_do_mais_recente_para_o_mais_antigo(self):
        antigo = self.privado('antigo', momento(10, 9))
        recente = self.privado('recente', momento(20, 18))
        meio = self.privado('meio', momento(15, 12))
        self.entrar(self.napne)
        self.assertEqual(self.ids_da_pagina('listar_feedbacks_privados'), [recente.id, meio.id, antigo.id])

    def test_a_hora_decide_entre_feedbacks_do_mesmo_dia(self):
        manha = self.publico('manha', momento(20, 8, 0))
        tarde = self.publico('tarde', momento(20, 16, 30))
        self.entrar(self.napne)
        self.assertEqual(self.ids_da_pagina('listar_feedbacks_publicos'), [tarde.id, manha.id])

    def test_empate_no_mesmo_instante_desempata_pelo_id_mais_novo(self):
        instante = momento(20, 10)
        primeiro = self.publico('primeiro', instante)
        segundo = self.publico('segundo', instante)
        primeiro_privado = self.privado('primeiro', instante)
        segundo_privado = self.privado('segundo', instante)
        self.entrar(self.napne)
        self.assertEqual(self.ids_da_pagina('listar_feedbacks_publicos'), [segundo.id, primeiro.id])
        self.assertEqual(self.ids_da_pagina('listar_feedbacks_privados'), [segundo_privado.id, primeiro_privado.id])


class ConteudoDasListasTests(BaseFeedbacks):
    def test_lista_publica_mostra_autor_noticia_conteudo_data_e_link_do_detalhe(self):
        feedback = self.publico('Ótima matéria sobre acessibilidade', momento(21, 14, 30))
        self.entrar(self.napne)
        resposta = self.client.get(reverse('listar_feedbacks_publicos'))

        self.assertContains(resposta, 'Aluno')
        self.assertContains(resposta, 'Semana da Inclusão')
        self.assertContains(resposta, 'Ótima matéria sobre acessibilidade')
        self.assertContains(resposta, '21/11/2026 14:30')
        self.assertContains(resposta, reverse('detalhe', args=[self.noticia.id]))
        self.assertContains(resposta, reverse('detalhar_feedback_publico', args=[feedback.id]))

    def test_lista_privada_mostra_autor_noticia_conteudo_data_e_link_do_detalhe(self):
        feedback = self.privado('Tenho uma dúvida particular', momento(21, 9, 5))
        self.entrar(self.napne)
        resposta = self.client.get(reverse('listar_feedbacks_privados'))

        self.assertContains(resposta, 'Aluno')
        self.assertContains(resposta, 'Semana da Inclusão')
        self.assertContains(resposta, 'Tenho uma dúvida particular')
        self.assertContains(resposta, '21/11/2026 09:05')
        self.assertContains(resposta, reverse('detalhar_feedback_privado', args=[feedback.id]))

    def test_lista_privada_indica_quando_nao_ha_noticia(self):
        self.privado('Sem vínculo', noticia=None)
        self.entrar(self.napne)
        resposta = self.client.get(reverse('listar_feedbacks_privados'))
        self.assertContains(resposta, 'Sem notícia')

    def test_cada_lista_mostra_apenas_o_seu_tipo_de_feedback(self):
        self.publico('texto-publico-unico')
        self.privado('texto-privado-unico')
        self.entrar(self.napne)
        publicos = self.client.get(reverse('listar_feedbacks_publicos'))
        privados = self.client.get(reverse('listar_feedbacks_privados'))
        self.assertContains(publicos, 'texto-publico-unico')
        self.assertNotContains(publicos, 'texto-privado-unico')
        self.assertContains(privados, 'texto-privado-unico')
        self.assertNotContains(privados, 'texto-publico-unico')

    def test_listas_vazias_mostram_a_mensagem_de_vazio(self):
        self.entrar(self.napne)
        self.assertContains(self.client.get(reverse('listar_feedbacks_publicos')), 'Nenhum feedback público foi enviado ainda.')
        self.assertContains(self.client.get(reverse('listar_feedbacks_privados')), 'Nenhum feedback privado foi enviado ainda.')


class PaginacaoDosFeedbacksTests(BaseFeedbacks):
    def test_lista_publica_e_paginada(self):
        for numero in range(16):
            self.publico(f'comentario {numero}', momento(1 + numero if numero < 20 else 20, 8))
        self.entrar(self.napne)
        url = reverse('listar_feedbacks_publicos')

        primeira = self.client.get(url)
        self.assertEqual(len(primeira.context['feedbacks']), 15)
        self.assertContains(primeira, '?page=2')

        segunda = self.client.get(url, {'page': 2})
        self.assertEqual(len(segunda.context['feedbacks']), 1)
        self.assertContains(segunda, 'comentario 0')

    def test_lista_privada_e_paginada(self):
        for numero in range(16):
            self.privado(f'mensagem {numero}', momento(1 + numero, 8))
        self.entrar(self.napne)
        url = reverse('listar_feedbacks_privados')

        self.assertEqual(len(self.client.get(url).context['feedbacks']), 15)
        self.assertEqual(len(self.client.get(url, {'page': 2}).context['feedbacks']), 1)

    def test_pagina_invalida_nao_quebra(self):
        self.publico()
        self.entrar(self.napne)
        for valor in ('999', 'abc'):
            with self.subTest(page=valor):
                resposta = self.client.get(reverse('listar_feedbacks_publicos'), {'page': valor})
                self.assertEqual(resposta.status_code, 200)


class AcessoAsListasDeFeedbackTests(BaseFeedbacks):
    ROTAS = ('listar_feedbacks_publicos', 'listar_feedbacks_privados')

    def test_visitante_anonimo_e_enviado_para_o_login(self):
        for rota in self.ROTAS:
            with self.subTest(rota=rota):
                resposta = self.client.get(reverse(rota))
                self.assertEqual(resposta.status_code, 302)
                self.assertIn('login', resposta.url)

    def test_quem_nao_e_do_napne_recebe_acesso_negado(self):
        for quem in (self.estudante, self.professor, self.pendente):
            self.client.logout()
            self.entrar(quem)
            for rota in self.ROTAS:
                with self.subTest(usuario=quem.username, rota=rota):
                    self.assertEqual(self.client.get(reverse(rota)).status_code, 403)

    def test_napne_acessa(self):
        self.entrar(self.napne)
        for rota in self.ROTAS:
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(reverse(rota)).status_code, 200)


class MenuEDetalheTests(BaseFeedbacks):
    def test_menu_do_painel_tem_o_item_feedbacks_publicos(self):
        itens = settings.ADMINLTE['menu']
        self.assertTrue(any('listar_feedbacks_publicos' in str(item) for item in itens))

    def test_detalhe_publico_mostra_data_e_hora_para_o_napne(self):
        feedback = self.publico('Comentário com hora', momento(21, 14, 30))
        self.entrar(self.napne)
        resposta = self.client.get(reverse('detalhar_feedback_publico', args=[feedback.id]))
        self.assertContains(resposta, '21/11/2026 14:30')

    def test_detalhe_privado_mostra_data_e_hora_para_o_napne(self):
        feedback = self.privado('Mensagem com hora', momento(21, 9, 5))
        self.entrar(self.napne)
        resposta = self.client.get(reverse('detalhar_feedback_privado', args=[feedback.id]))
        self.assertContains(resposta, '21/11/2026 09:05')
