from django.contrib import messages
from django.contrib.auth.models import Group
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import napne_required
from .forms import ApresentacaoNapneForm, ImagemCarrosselFormSet, NoticiaForm, PeiForm
from .models import ApresentacaoNapne, Noticia, Pei, SolicitacaoNapne


@napne_required
def painel_home(request):
    context = {
        'total_noticias': Noticia.objects.count(),
        'total_peis': Pei.objects.count(),
        'total_solicitacoes_pendentes': SolicitacaoNapne.objects.filter(status=SolicitacaoNapne.PENDENTE).count(),
    }
    return render(request, "core/painel_home.html", context)

@napne_required
def criar_noticia(request):
    if request.method == 'POST':
        form = NoticiaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = NoticiaForm()
    return render(request, 'core/criar_noticia.html', {'form': form})

@napne_required
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

@napne_required
def excluir_noticia(request, id):
    noticia = get_object_or_404(Noticia, id=id)
    if request.method == 'POST':
        noticia.delete()
        return redirect('index')
    return render(request, 'core/excluir_noticia.html', {'noticia': noticia})

@napne_required
def listar_peis(request):
    peis = Pei.objects.all()
    context = {'peis': peis}
    return render(request, 'core/listar_peis.html', context)

@napne_required
def excluir_pei(request, id):
    pei = get_object_or_404(Pei, id=id)
    if request.method == 'POST':
        pei.delete()
        return redirect('listar_peis')
    return render(request, 'core/excluir_pei.html', {'pei': pei})

@napne_required
def detalhar_pei(request, id):
    pei = get_object_or_404(Pei, id=id)
    context = {'pei': pei}
    return render(request, 'core/detalhar_pei.html', context)

@napne_required
def editar_pei(request, id):
    pei = get_object_or_404(Pei, id=id)
    if request.method == 'POST':
        form = PeiForm(request.POST, request.FILES, instance=pei)
        if form.is_valid():
            form.save()
            return redirect('detalhar_pei', id=pei.id)
    else:
        form = PeiForm(instance=pei)
    return render(request, 'core/editar_pei.html', {'form': form, 'pei': pei})

@napne_required
def baixar_pei(request, id):
    pei = get_object_or_404(Pei, id=id)
    response = FileResponse(pei.arquivo.open(), as_attachment=True, filename=pei.arquivo.name)
    response['Content-disposition'] = f'attachment; filename="{pei.arquivo.name}"'
    return response

@napne_required
def solicitacoes_napne(request):
    solicitacoes = SolicitacaoNapne.objects.filter(status=SolicitacaoNapne.PENDENTE).select_related('user')
    return render(request, 'core/solicitacoes_napne.html', {'solicitacoes': solicitacoes})

@napne_required
def aprovar_solicitacao_napne(request, id):
    solicitacao = get_object_or_404(SolicitacaoNapne, id=id)
    if request.method == 'POST':
        grupo_napne, _ = Group.objects.get_or_create(name="NAPNE")
        solicitacao.user.groups.add(grupo_napne)
        solicitacao.status = SolicitacaoNapne.APROVADO
        solicitacao.avaliado_por = request.user
        solicitacao.avaliado_em = timezone.now()
        solicitacao.save()
        messages.success(request, f'{solicitacao.user.get_full_name()} foi aprovado(a) como membro do NAPNE.')
    return redirect('solicitacoes_napne')

@napne_required
def recusar_solicitacao_napne(request, id):
    solicitacao = get_object_or_404(SolicitacaoNapne, id=id)
    if request.method == 'POST':
        solicitacao.status = SolicitacaoNapne.RECUSADO
        solicitacao.avaliado_por = request.user
        solicitacao.avaliado_em = timezone.now()
        solicitacao.save()
        messages.info(request, f'A solicitação de {solicitacao.user.get_full_name()} foi recusada.')
    return redirect('solicitacoes_napne')

@napne_required
def editar_apresentacao_napne(request):
    apresentacao = ApresentacaoNapne.obter_instancia()
    if request.method == 'POST':
        form = ApresentacaoNapneForm(request.POST, instance=apresentacao)
        formset = ImagemCarrosselFormSet(request.POST, request.FILES, instance=apresentacao)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Tela de apresentação do NAPNE atualizada com sucesso!')
            return redirect('editar_apresentacao_napne')
    else:
        form = ApresentacaoNapneForm(instance=apresentacao)
        formset = ImagemCarrosselFormSet(instance=apresentacao)
    return render(request, 'core/editar_apresentacao_napne.html', {'form': form, 'formset': formset})