from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, request
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.decorators import professor_required
from core.forms import CadastroNapneForm, LoginNapneForm, PeiForm, FeedbackPublicoForm, FeedbackPrivadoForm
from core.models import FeedbackPrivado, FeedbackPublico, Noticia, SolicitacaoNapne



def index(request):
    noticias = Noticia.objects.all().order_by('-data')
    paginator = Paginator(noticias, 9)  
    num_pag = request.GET.get('page')
    page = paginator.get_page(num_pag)
    elided = paginator.get_elided_page_range(number=page.number, on_each_side=2, on_ends=2)
    context = {'noticias': page, 'elided': elided}
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
    termo = request.GET.get('q', '')
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
