from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import professor_required
from core.forms import PeiForm
from core.models import Noticia


def index(request):
    noticias = Noticia.objects.all()
    context = {'noticias': noticias}
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