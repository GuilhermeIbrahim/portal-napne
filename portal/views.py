from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import professor_required
from core.forms import PeiForm
from core.models import Noticia
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse


def index(request):
    noticias = Noticia.objects.all()
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