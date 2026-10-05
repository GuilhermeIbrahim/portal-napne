from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from core.decorators import professor_required
from core.forms import (
    CadastroNapneForm,
    FeedbackPrivadoForm,
    FeedbackPublicoForm,
    LoginNapneForm,
    PeiForm,
)
from core.models import (
    ApresentacaoNapne,
    FeedbackPrivado,
    FeedbackPublico,
    Noticia,
    Notificacao,
    SolicitacaoNapne,
)


def index(request):
    ultimo_noticia_id = Noticia.objects.aggregate(ultimo=Max('id'))['ultimo'] or 0
    noticias = Noticia.objects.all().order_by('-data', '-id')
    paginator = Paginator(noticias, 9)  
    num_pag = request.GET.get('page')
    page = paginator.get_page(num_pag)
    elided = paginator.get_elided_page_range(number=page.number, on_each_side=2, on_ends=2)

    notificacoes_nao_lidas = Notificacao.nao_lidas_para(request.user)

    context = {'noticias': page, 'elided': elided, 'notificacoes_nao_lidas': notificacoes_nao_lidas, 'ultimo_noticia_id': ultimo_noticia_id}
    return render(request, "portal/index.html", context) 

def detalhe(request, id):
    noticia = get_object_or_404(Noticia, id=id)
    context = {'noticia': noticia}
    return render(request, "portal/detalhe.html", context)


@professor_required
def enviar_pei(request):
    if request.method == 'POST':
        form = PeiForm(request.POST, request.FILES)
        if form.is_valid():
            pei = form.save(commit=False)
            pei.professor = request.user
            pei.save()
            messages.success(request, 'PEI enviado com sucesso!')
            return redirect('index')
    else:
        form = PeiForm()
    return render(request, 'portal/enviar_pei.html', {'form': form})

def pesquisar_noticias(request):
    termo = request.GET.get('q', '').strip()
    resultados = []
    if termo:
        noticias = Noticia.objects.filter(Q(titulo__icontains=termo) | Q(conteudo__icontains=termo))
        for noticia in noticias:
            resultados.append({
                'id': noticia.id,
                'titulo': noticia.titulo,
                'url': reverse('detalhe', args=[noticia.id]),
            })
    return JsonResponse({'resultados': resultados})

def cadastro_napne(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = CadastroNapneForm(request.POST)
        if form.is_valid():
            user = form.save()
            SolicitacaoNapne.objects.create(user=user)
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(
                request,
                'Cadastro enviado! Sua conta foi criada e já está logada, mas ainda precisa ser '
                'aprovada por um membro do NAPNE antes de ter acesso ao painel.',
            )
            return redirect('index')
    else:
        form = CadastroNapneForm()
    return render(request, 'portal/cadastro_napne.html', {'form': form})

def login_napne(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = LoginNapneForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect(request.GET.get('next') or 'index')
    else:
        form = LoginNapneForm()
    return render(request, 'portal/login_napne.html', {'form': form})

def fazer_feedback_publico(request, noticia_id):
    noticia = get_object_or_404(Noticia, id=noticia_id)
    if request.method == 'POST':
        form = FeedbackPublicoForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.noticia = noticia
            feedback.autor = request.user
            feedback.save()
            messages.success(request, 'Comentário enviado com sucesso!')
            return redirect('detalhe', id=noticia.id)
    else:
        form = FeedbackPublicoForm()
    return render(request, 'portal/fazer_feedback_publico.html', {'form': form, 'noticia': noticia})

def fazer_feedback_privado(request,):
    noticia = request.GET.get('noticia')
    noticia_vinculada = Noticia.objects.filter(id=noticia).first() if noticia else None
    meus_feedbacks = FeedbackPrivado.objects.filter(autor=request.user).order_by('-data')
    if request.method == 'POST':
        form = FeedbackPrivadoForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.autor = request.user
            feedback.save()
            messages.success(request, 'Feedback privado enviado com sucesso!')
            return redirect('index')
        else:
            form = FeedbackPrivadoForm(initial={'noticia': noticia})
    else:
        form = FeedbackPrivadoForm(initial={'noticia': noticia})

    return render(request, 'portal/fazer_feedback_privado.html', {'form': form, 'noticia_vinculada': noticia_vinculada, 'meus_feedbacks': meus_feedbacks})


def excluir_feedback_publico(request, feedback_id):
    feedback = get_object_or_404(FeedbackPublico, id=feedback_id)
    eh_autor = request.user == feedback.autor
    eh_napne = request.user.groups.filter(name="NAPNE").exists()

    if eh_autor or eh_napne:
        confirmacao = request.POST.get('confirmacao')
        if confirmacao == 'sim':
            feedback.delete()
            messages.success(request, 'Comentário excluído com sucesso!')
        else:
            messages.info(request, 'Exclusão de comentário cancelada.')
    else:
        messages.error(request, 'Você não tem permissão para excluir este comentário.')
        
    return redirect('detalhe', id=feedback.noticia.id)


def editar_feedback_publico(request, feedback_id):
    feedback = get_object_or_404(FeedbackPublico, id=feedback_id)
    eh_autor = request.user == feedback.autor

    if not eh_autor:
        messages.error(request, 'Você não tem permissão para editar este comentário.')
        return redirect('detalhe', id=feedback.noticia.id)

    if request.method == 'POST':
        form = FeedbackPublicoForm(request.POST, instance=feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.editado_em = timezone.now()
            form.save()
            messages.success(request, 'Comentário editado com sucesso!')
            return redirect('detalhe', id=feedback.noticia.id)
    else:
        form = FeedbackPublicoForm(instance=feedback)

    return render(request, 'portal/editar_feedback_publico.html', {'form': form, 'feedback': feedback})


def editar_feedback_privado(request, feedback_id):
    feedback = get_object_or_404(FeedbackPrivado, id=feedback_id)
    eh_autor = request.user == feedback.autor

    if not eh_autor:
        messages.error(request, 'Você não tem permissão para editar este feedback privado.')
        return redirect('index')

    if request.method == 'POST':
        form = FeedbackPrivadoForm(request.POST, instance=feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.editado_em = timezone.now()
            form.save()
            messages.success(request, 'Feedback privado editado com sucesso!')
            return redirect('index')
    else:
        form = FeedbackPrivadoForm(instance=feedback)

    return render(request, 'portal/editar_feedback_privado.html', {'form': form, 'feedback': feedback})

def detalhar_feedback_privado(request, feedback_id):
    feedback = get_object_or_404(FeedbackPrivado, id=feedback_id)
    eh_autor = request.user == feedback.autor
    eh_napne = request.user.groups.filter(name="NAPNE").exists()

    if not (eh_autor or eh_napne):
        messages.error(request, 'Você não tem permissão para visualizar este feedback privado.')
        return redirect('index')

    return render(request, 'portal/detalhar_feedback_privado.html', {'feedback': feedback})

def detalhar_feedback_publico(request, feedback_id):
    feedback = get_object_or_404(FeedbackPublico, id=feedback_id)
    eh_autor = request.user == feedback.autor
    eh_napne = request.user.groups.filter(name="NAPNE").exists()

    if not (eh_autor or eh_napne):
        messages.error(request, 'Você não tem permissão para visualizar este comentário.')
        return redirect('index')

    return render(request, 'portal/detalhar_feedback_publico.html', {'feedback': feedback})
def apresentacao_napne(request):
    apresentacao = ApresentacaoNapne.obter_instancia()
    context = {'apresentacao': apresentacao}
    return render(request, 'portal/apresentacao_napne.html', context)

@login_required
def detalhar_notificacao(request, id):
    notificacao = get_object_or_404(Notificacao, id=id)

    if not notificacao.visivel_para(request.user):
        raise PermissionDenied("Esta notificação não é destinada a você.")

    notificacao.lida_por.add(request.user)

    context = {'notificacao': notificacao}
    return render(request, 'portal/detalhar_notificacao.html', context)


@login_required
def minhas_notificacoes(request):
    notificacoes = list(Notificacao.para_usuario(request.user))
    lidas_ids = set(request.user.notificacoes_lidas.values_list('id', flat=True))
    for notificacao in notificacoes:
        notificacao.nao_lida = notificacao.id not in lidas_ids
    return render(request, 'portal/minhas_notificacoes.html', {'notificacoes': notificacoes})

# ---------------------------------------------------------------------------
# Atualização automática (AJAX com polling)
# ---------------------------------------------------------------------------
LIMITE_NOTICIAS_POR_CONSULTA = 12
LIMITE_NOTIFICACOES_TOAST = 5
LIMITE_NOTIFICACOES_LISTA = 20
TAMANHO_TRECHO_NOTIFICACAO = 120


def _ler_desde(request):
    bruto = request.GET.get('desde')
    if bruto in (None, ''):
        return None
    valor = int(bruto)
    if valor < 0:
        raise ValueError('desde negativo')
    return valor


@require_GET
@never_cache
def api_noticias_novas(request):
    try:
        desde = _ler_desde(request)
    except ValueError:
        return JsonResponse({'erro': 'Parâmetro "desde" inválido.'}, status=400)

    ultimo_id = Noticia.objects.aggregate(ultimo=Max('id'))['ultimo'] or 0

    if desde is None:
        return JsonResponse({'ultimo_id': ultimo_id, 'total': 0, 'html': ''})

    novas = Noticia.objects.filter(id__gt=desde)
    total = novas.count()
    cards = [
        render_to_string('portal/partials/_card_noticia.html', {'noticia': noticia, 'novo': True}, request=request)
        for noticia in novas.order_by('-id')[:LIMITE_NOTICIAS_POR_CONSULTA]
    ]
    return JsonResponse({'ultimo_id': ultimo_id, 'total': total, 'html': ''.join(cards)})


@require_GET
@never_cache
def api_notificacoes_novas(request):
    if not request.user.is_authenticated:
        return JsonResponse({'erro': 'Faça login para ver suas notificações.'}, status=401)

    try:
        desde = _ler_desde(request)
    except ValueError:
        return JsonResponse({'erro': 'Parâmetro "desde" inválido.'}, status=400)

    visiveis = Notificacao.para_usuario(request.user)
    nao_lidas = Notificacao.nao_lidas_para(request.user)

    resposta = {
        'ultimo_id': visiveis.aggregate(ultimo=Max('id'))['ultimo'] or 0,
        'nao_lidas': nao_lidas.count(),
        'total_novas': 0,
        'novas': [],
        'html': '',
    }

    if desde is None:
        return JsonResponse(resposta)

    novas_qs = nao_lidas.filter(id__gt=desde)
    resposta['total_novas'] = novas_qs.count()
    novas = list(novas_qs.order_by('id')[:LIMITE_NOTIFICACOES_LISTA])

    resposta['novas'] = [
        {
            'id': notificacao.id,
            'titulo': notificacao.titulo,
            'trecho': Truncator(strip_tags(notificacao.conteudo)).chars(TAMANHO_TRECHO_NOTIFICACAO),
            'url': reverse('detalhar_notificacao', args=[notificacao.id]),
        }
        for notificacao in novas[:LIMITE_NOTIFICACOES_TOAST]
    ]

    if request.GET.get('lista') == '1':
        itens = []
        for notificacao in reversed(novas):  
            notificacao.nao_lida = True
            itens.append(render_to_string(
                'portal/partials/_item_notificacao.html',
                {'notificacao': notificacao, 'novo': True},
                request=request,
            ))
        resposta['html'] = ''.join(itens)

    return JsonResponse(resposta)