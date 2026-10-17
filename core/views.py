from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import napne_required
from .downloads import resposta_de_download
from .forms import (
    AnalisePeiForm,
    ApresentacaoNapneForm,
    EditarPeiForm,
    ImagemCarrosselFormSet,
    NoticiaForm,
    NotificacaoForm,
)
from .models import (
    ApresentacaoNapne,
    FeedbackPrivado,
    Noticia,
    Notificacao,
    Pei,
    RegistroAcessoPei,
    SolicitacaoNapne,
    TransicaoPeiInvalida,
    VersaoPei,
)
from .validators import normalizar_periodo_letivo


@napne_required
def painel_home(request):
    context = {
        'total_noticias': Noticia.objects.count(),
        'total_peis': Pei.objects.count(),
        'total_solicitacoes_pendentes': SolicitacaoNapne.objects.filter(status=SolicitacaoNapne.PENDENTE).count(),
        'total_peis_em_analise': Pei.objects.filter(status=Pei.EM_ANALISE).count(),
    }
    return render(request, "core/painel_home.html", context)

@napne_required
def criar_noticia(request):
    if request.method == 'POST':
        form = NoticiaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('painel_home')
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
        return redirect('painel_home')
    return render(request, 'core/excluir_noticia.html', {'noticia': noticia})

@napne_required
def listar_peis(request):
    status = request.GET.get('status', '')
    periodo = normalizar_periodo_letivo(request.GET.get('periodo', ''))
    peis = Pei.objects.select_related('professor').annotate(ultima_versao=Max('versoes__numero')).order_by('-data_envio', '-id')

    if status in dict(Pei.STATUS_CHOICES):
        peis = peis.filter(status=status)
    else:
        status = ''

    periodos_existentes = list(
        Pei.objects.exclude(periodo_letivo='').order_by('-periodo_letivo').values_list('periodo_letivo', flat=True).distinct()
    )
    if periodo in periodos_existentes:
        peis = peis.filter(periodo_letivo=periodo)
    else:
        periodo = ''

    context = {
        'peis': peis,
        'status_atual': status,
        'status_choices': Pei.STATUS_CHOICES,
        'periodo_atual': periodo,
        'periodos': periodos_existentes,
    }
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
    pei = get_object_or_404(Pei.objects.select_related('professor'), id=id)
    form = AnalisePeiForm()

    if request.method == 'POST':
        if not pei.pode_ser_analisado():
            messages.error(
                request,
                f'Só é possível registrar decisão em PEI "Em análise" (status atual: {pei.get_status_display()}).',
            )
            return redirect('detalhar_pei', id=pei.id)

        form = AnalisePeiForm(request.POST)
        if form.is_valid():
            try:
                pei.registrar_analise(
                    form.cleaned_data['decisao'],
                    form.cleaned_data['parecer'],
                    request.user,
                    request=request,
                )
            except TransicaoPeiInvalida as erro:
                messages.error(request, str(erro))
                return redirect('detalhar_pei', id=pei.id)

            messages.success(
                request,
                f'Análise registrada: o PEI agora está "{pei.get_status_display()}" e o professor foi notificado.',
            )
            return redirect('detalhar_pei', id=pei.id)

    if request.method == 'GET':
        RegistroAcessoPei.registrar(request.user, pei, RegistroAcessoPei.VISUALIZOU)

    context = {
        'pei': pei,
        'form': form,
        'historico': pei.historico.select_related('alterado_por', 'versao'),
        'versoes': pei.versoes.select_related('enviado_por'),
    }
    return render(request, 'core/detalhar_pei.html', context)

@napne_required
def editar_pei(request, id):
    pei = get_object_or_404(Pei, id=id)
    if request.method == 'POST':
        form = EditarPeiForm(request.POST, instance=pei)
        if form.is_valid():
            form.save()
            return redirect('detalhar_pei', id=pei.id)
    else:
        form = EditarPeiForm(instance=pei)
    return render(request, 'core/editar_pei.html', {'form': form, 'pei': pei})

@napne_required
def baixar_pei(request, id):
    pei = get_object_or_404(Pei, id=id)
    versao = pei.versao_atual
    RegistroAcessoPei.registrar(request.user, pei, RegistroAcessoPei.BAIXOU, versao)
    return resposta_de_download(pei.arquivo, versao.nome_do_download() if versao else None)

@napne_required
def baixar_versao_pei(request, versao_id):
    versao = get_object_or_404(VersaoPei.objects.select_related('pei'), id=versao_id)
    RegistroAcessoPei.registrar(request.user, versao.pei, RegistroAcessoPei.BAIXOU, versao)
    return resposta_de_download(versao.arquivo, versao.nome_do_download())

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
def listar_feedbacks_privados(request):
    feedbacks = FeedbackPrivado.objects.select_related('autor', 'noticia').order_by('-data')
    context = {'feedbacks': feedbacks}
    return render(request, 'core/listar_feedbacks_privados.html', context)

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


@napne_required
def listar_notificacoes(request):
    notificacoes = Notificacao.objects.all()
    context = {'notificacoes': notificacoes}
    return render(request, 'core/listar_notificacoes.html', context)


@napne_required
def criar_notificacao(request):
    if request.method == 'POST':
        form = NotificacaoForm(request.POST)
        if form.is_valid():
            notificacao = form.save(commit=False)
            notificacao.remetente = request.user
            notificacao.save()
            messages.success(request, 'Notificação enviada com sucesso!')
            return redirect('listar_notificacoes')
    else:
        form = NotificacaoForm()
    return render(request, 'core/criar_notificacao.html', {'form': form})


@napne_required
def editar_notificacao(request, id):
    notificacao = get_object_or_404(Notificacao, id=id)
    if request.method == 'POST':
        form = NotificacaoForm(request.POST, instance=notificacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notificação atualizada com sucesso!')
            return redirect('listar_notificacoes')
    else:
        form = NotificacaoForm(instance=notificacao)
    return render(request, 'core/editar_notificacao.html', {'form': form, 'notificacao': notificacao})


@napne_required
def excluir_notificacao(request, id):
    notificacao = get_object_or_404(Notificacao, id=id)
    if request.method == 'POST':
        notificacao.delete()
        messages.success(request, 'Notificação excluída com sucesso!')
        return redirect('listar_notificacoes')
    return render(request, 'core/excluir_notificacao.html', {'notificacao': notificacao})
