from django.shortcuts import render
from .models import Noticia
from django.shortcuts import get_object_or_404, redirect
from  .forms import NoticiaForm
from django.contrib.auth.decorators import login_required

def index(request):
    noticias = Noticia.objects.all()
    context = {'noticias': noticias}
    return render(request, "core/index.html", context)

def detalhe(request, id):
    noticia = get_object_or_404(Noticia, id=id)
    context = {'noticia': noticia}
    return render(request, "core/detalhe.html", context)

@login_required
def criar_noticia(request):
    if request.method == 'POST':
        form = NoticiaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = NoticiaForm()
    return render(request, 'core/criar_noticia.html', {'form': form})

@login_required
def editar_noticia(request, id):
    noticia = get_object_or_404(Noticia, id=id)
    if request.method == 'POST':
        form = NoticiaForm(request.POST, request.FILES, instance=noticia)
        if form.is_valid():
            form.save()
            return redirect('detalhe', id=noticia.id)
    else:
        form = NoticiaForm(instance=noticia)
    return render(request, 'core/editar_noticia.html', {'form': form, 'noticia': noticia})

@login_required
def excluir_noticia(request, id):
    noticia = get_object_or_404(Noticia, id=id)
    if request.method == 'POST':
        noticia.delete()
        return redirect('index')
    return render(request, 'core/excluir_noticia.html', {'noticia': noticia})