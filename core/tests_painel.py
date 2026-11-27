from unittest import mock

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from . import painel
from .models import FeedbackPrivado, FeedbackPublico, Noticia, Notificacao, SolicitacaoNapne
from .painel import CONFIGURACAO_DOS_CARDS, cards_do_painel, itens_do_menu
from .tests import HASH_RAPIDO, MEDIA_TESTE, PRIVADO_TESTE, BaseTestes

SENHA = 'senha-forte-123'


@override_settings(MEDIA_ROOT=MEDIA_TESTE, PEI_ARMAZENAMENTO_PRIVADO=PRIVADO_TESTE, PASSWORD_HASHERS=HASH_RAPIDO)
class CardsDoPainelTests(BaseTestes):
    def entrar(self, usuario):
        self.client.logout()
        self.client.login(username=usuario.username, password=SENHA)

    def pagina(self):
        self.entrar(self.napne)
        resposta = self.client.get(reverse('painel_home'))
        self.assertEqual(resposta.status_code, 200)
        return resposta

    def test_todo_item_do_menu_tem_um_card_na_tela_inicial(self):
        resposta = self.pagina()
        html = resposta.content.decode()
        rotas_com_card = [card['rota'] for card in resposta.context['cards']]
        for item in settings.ADMINLTE['menu']:
            if item['route'] == 'painel_home':
                continue
            with self.subTest(item=item['text']):
                self.assertIn(item['route'], rotas_com_card)
                self.assertIn(f'data-card-painel="{item["route"]}"', html)
                self.assertContains(resposta, f'href="{reverse(item["route"])}"')

    def test_a_quantidade_de_cards_e_a_do_menu_sem_o_proprio_painel(self):
        esperado = len([i for i in settings.ADMINLTE['menu'] if i['route'] != 'painel_home'])
        self.assertEqual(len(self.pagina().context['cards']), esperado)

    def test_os_cards_seguem_a_ordem_do_menu(self):
        rotas_do_menu = [i['route'] for i in settings.ADMINLTE['menu'] if i['route'] != 'painel_home']
        self.assertEqual([c['rota'] for c in self.pagina().context['cards']], rotas_do_menu)

    def test_todo_item_do_menu_tem_descricao_configurada(self):
        """Falha quando alguém cria um item de menu novo e esquece de descrever o card dele."""
        for item in itens_do_menu():
            with self.subTest(item=item['text']):
                self.assertIn(item['route'], CONFIGURACAO_DOS_CARDS)
                self.assertTrue(CONFIGURACAO_DOS_CARDS[item['route']].get('descricao'))

    def test_item_novo_no_menu_ganha_card_automaticamente(self):
        menu = list(settings.ADMINLTE['menu']) + [
            {'text': 'Item novo de teste', 'route': 'listar_notificacoes', 'icon': 'bi bi-star'},
        ]
        with override_settings(ADMINLTE={**settings.ADMINLTE, 'menu': menu}):
            cards = cards_do_painel()
        self.assertEqual(cards[-1]['texto'], 'Item novo de teste')
        self.assertEqual(cards[-1]['icone'], 'bi bi-star')
        self.assertEqual(cards[-1]['url'], reverse('listar_notificacoes'))

    def test_item_sem_configuracao_ainda_ganha_card_basico(self):
        with mock.patch.dict(painel.CONFIGURACAO_DOS_CARDS, clear=True):
            cards = cards_do_painel()
        self.assertEqual(len(cards), len(itens_do_menu()))
        self.assertTrue(all(card['descricao'] == '' and card['metricas'] == [] for card in cards))

    def test_card_mostra_a_descricao_o_titulo_e_o_link(self):
        resposta = self.pagina()
        self.assertContains(resposta, 'Aprove ou recuse pedidos de acesso ao NAPNE.')
        self.assertContains(resposta, 'Solicitações NAPNE')

    def test_numeros_dos_cards(self):
        noticia = Noticia.objects.create(titulo='N1', conteudo='x')
        Noticia.objects.create(titulo='N2', conteudo='x')
        FeedbackPublico.objects.create(noticia=noticia, conteudo='c', autor=self.estudante)
        FeedbackPrivado.objects.create(noticia=noticia, conteudo='p', autor=self.estudante)
        FeedbackPrivado.objects.create(noticia=None, conteudo='p2', autor=self.estudante)
        Notificacao.objects.create(titulo='A', conteudo='a', remetente=self.napne)
        SolicitacaoNapne.objects.get_or_create(user=self.pendente)

        cards = {c['rota']: c['metricas'] for c in self.pagina().context['cards']}

        self.assertEqual(cards['criar_noticia'], [(2, 'notícia(s) publicada(s)')])
        self.assertEqual(cards['listar_peis'], [(1, 'PEI(s) recebido(s)'), (1, 'aguardando análise')])
        self.assertEqual(cards['solicitacoes_napne'][0][0], 1)
        self.assertEqual(cards['listar_feedbacks_privados'][0][0], 2)
        self.assertEqual(cards['listar_notificacoes'][0][0], 1)
        if 'listar_feedbacks_publicos' in cards:
            self.assertEqual(cards['listar_feedbacks_publicos'][0][0], 1)

    def test_acesso_ao_painel_continua_restrito_ao_napne(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('painel_home')).status_code, 302)
        for quem in (self.estudante, self.professor, self.pendente):
            self.entrar(quem)
            self.assertEqual(self.client.get(reverse('painel_home')).status_code, 403)
