"""Cards da tela inicial do painel do NAPNE.

Os cards são gerados a partir de ``settings.ADMINLTE["menu"]``: cada item do menu
lateral ganha um card, na mesma ordem. Para dar descrição e números a um item novo,
basta acrescentar uma entrada em ``CONFIGURACAO_DOS_CARDS`` com a mesma ``route`` do menu.
"""
from django.conf import settings
from django.urls import reverse

from .models import FeedbackPrivado, FeedbackPublico, Noticia, Notificacao, Pei, SolicitacaoNapne

# O próprio painel não ganha card (seria um link para a página em que o card está).
ROTAS_SEM_CARD = {'painel_home'}


def _metricas_peis():
    return [
        (Pei.objects.count(), 'PEI(s) recebido(s)'),
        (Pei.objects.filter(status=Pei.EM_ANALISE).count(), 'aguardando análise'),
    ]


# route do menu -> descrição e (opcional) função que devolve a lista de (número, rótulo)
CONFIGURACAO_DOS_CARDS = {
    'criar_noticia': {
        'descricao': 'Publique uma nova notícia no portal.',
        'metricas': lambda: [(Noticia.objects.count(), 'notícia(s) publicada(s)')],
    },
    'listar_peis': {
        'descricao': 'Acompanhe e analise os PEIs enviados pelos professores.',
        'metricas': _metricas_peis,
    },
    'solicitacoes_napne': {
        'descricao': 'Aprove ou recuse pedidos de acesso ao NAPNE.',
        'metricas': lambda: [(
            SolicitacaoNapne.objects.filter(status=SolicitacaoNapne.PENDENTE).count(),
            'solicitação(ões) pendente(s)',
        )],
    },
    'listar_feedbacks_publicos': {
        'descricao': 'Comentários que os usuários deixaram nas notícias.',
        'metricas': lambda: [(FeedbackPublico.objects.count(), 'comentário(s) recebido(s)')],
    },
    'listar_feedbacks_privados': {
        'descricao': 'Mensagens privadas enviadas ao NAPNE.',
        'metricas': lambda: [(FeedbackPrivado.objects.count(), 'feedback(s) recebido(s)')],
    },
    'listar_notificacoes': {
        'descricao': 'Avisos enviados aos usuários do portal.',
        'metricas': lambda: [(Notificacao.objects.count(), 'notificação(ões) cadastrada(s)')],
    },
    'editar_apresentacao_napne': {
        'descricao': 'Título, texto e carrossel de imagens da tela "Sobre o NAPNE".',
    },
    'index': {
        'descricao': 'Veja o portal como os visitantes veem.',
    },
}


def itens_do_menu():
    """Itens do menu lateral que devem ter card (com ``route``), na ordem do menu."""
    return [
        item for item in settings.ADMINLTE.get('menu', [])
        if item.get('route') and item['route'] not in ROTAS_SEM_CARD
    ]


def cards_do_painel():
    cards = []
    for item in itens_do_menu():
        configuracao = CONFIGURACAO_DOS_CARDS.get(item['route'], {})
        funcao_metricas = configuracao.get('metricas')
        cards.append({
            'texto': item['text'],
            'icone': item.get('icon', 'bi bi-circle'),
            'rota': item['route'],
            'url': reverse(item['route']),
            'descricao': configuracao.get('descricao', ''),
            'metricas': funcao_metricas() if funcao_metricas else [],
        })
    return cards
