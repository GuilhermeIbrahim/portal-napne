from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.decorators import professor_required
from core.forms import CadastroNapneForm, LoginNapneForm, PeiForm
from core.models import ApresentacaoNapne, Noticia, SolicitacaoNapne


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

def apresentacao_napne(request):
    apresentacao = ApresentacaoNapne.obter_instancia()
    context = {'apresentacao': apresentacao}
    return render(request, 'portal/apresentacao_napne.html', context)
