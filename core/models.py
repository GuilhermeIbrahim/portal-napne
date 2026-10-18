import os
import re
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field

from .storage import armazenamento_privado_pei


class Usuario(AbstractUser):
    pass

class Noticia(models.Model):
    titulo = models.CharField(max_length=100)
    imagem = models.ImageField(upload_to="Noticias", null=True, blank=True)
    data = models.DateField(auto_now_add=True)
    conteudo = CKEditor5Field("Conteúdo", config_name="default")

    def __str__(self):
        return self.titulo

def caminho_arquivo_pei(instance, filename):
    extensao = os.path.splitext(filename)[1].lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,5}", extensao):
        extensao = ""
    return f"pei/{uuid.uuid4().hex}{extensao}"


class TransicaoPeiInvalida(Exception):
    """A operação não é permitida no status atual do PEI (ex.: analisar um PEI que não está em análise)."""


class Pei(models.Model):
    EM_ANALISE = "em_analise"
    ANALISADO = "analisado"
    DEVOLVIDO = "devolvido"
    AJUSTES_SOLICITADOS = "ajustes_solicitados"

    STATUS_CHOICES = [
        (EM_ANALISE, "Em análise"),
        (ANALISADO, "Analisado"),
        (DEVOLVIDO, "Devolvido"),
        (AJUSTES_SOLICITADOS, "Ajustes solicitados"),
    ]

    STATUS_BADGE = {
        EM_ANALISE: "warning",
        ANALISADO: "success",
        DEVOLVIDO: "danger",
        AJUSTES_SOLICITADOS: "info",
    }

    DECISAO_APROVAR = "aprovar"
    DECISAO_DEVOLVER = "devolver"
    DECISAO_AJUSTES = "ajustes"

    DECISOES = {
        DECISAO_APROVAR: ANALISADO,
        DECISAO_DEVOLVER: DEVOLVIDO,
        DECISAO_AJUSTES: AJUSTES_SOLICITADOS,
    }
    DECISOES_QUE_EXIGEM_PARECER = (DECISAO_DEVOLVER, DECISAO_AJUSTES)

    STATUS_AGUARDANDO_NOVA_VERSAO = (DEVOLVIDO, AJUSTES_SOLICITADOS)

    titulo = models.CharField(max_length=100)
    arquivo = models.FileField(upload_to=caminho_arquivo_pei, storage=armazenamento_privado_pei)
    data_envio = models.DateField(auto_now_add=True)
    professor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=EM_ANALISE)

    estudante_nome = models.CharField("Nome do estudante", max_length=150, blank=True, default="")
    estudante_matricula = models.CharField("Matrícula do estudante", max_length=20, blank=True, default="")
    estudante_curso = models.CharField("Curso do estudante", max_length=100, blank=True, default="")
    periodo_letivo = models.CharField("Período letivo", max_length=6, blank=True, default="")


    def __str__(self):
        return self.titulo

    def badge_theme(self):
        return self.STATUS_BADGE.get(self.status, "secondary")

    def save(self, *args, **kwargs):
        criando = self._state.adding
        super().save(*args, **kwargs)
        if criando and self.arquivo:
            VersaoPei.objects.create(
                pei=self,
                numero=1,
                arquivo=self.arquivo.name,
                enviado_por=self.professor,
            )

    def pode_ser_analisado(self):
        return self.status == self.EM_ANALISE

    def aguarda_nova_versao(self):
        return self.status in self.STATUS_AGUARDANDO_NOVA_VERSAO

    @property
    def versao_atual(self):
        return self.versoes.order_by("-numero").first()

    def registrar_analise(self, decisao, parecer, analista, request=None):
        if decisao not in self.DECISOES:
            raise ValueError(f"Decisão desconhecida: {decisao!r}")

        parecer = (parecer or "").strip()
        if decisao in self.DECISOES_QUE_EXIGEM_PARECER and not parecer:
            raise ValidationError({"parecer": "O parecer é obrigatório ao devolver ou solicitar ajustes."})

        novo_status = self.DECISOES[decisao]

        with transaction.atomic():
            pei = Pei.objects.select_for_update().get(pk=self.pk)
            if pei.status != self.EM_ANALISE:
                raise TransicaoPeiInvalida(
                    f"Só é possível registrar decisão em PEI \"Em análise\" (status atual: {pei.get_status_display()})."
                )

            historico = pei._registrar_mudanca(novo_status, analista, parecer)
            pei._notificar_professor_da_analise(novo_status, analista)

        self.status = novo_status
        return historico

    def enviar_nova_versao(self, arquivo, professor, comentario="", request=None):
        comentario = (comentario or "").strip()

        with transaction.atomic():
            pei = Pei.objects.select_for_update().get(pk=self.pk)

            if pei.professor_id != professor.id:
                raise PermissionDenied("Você não tem permissão para alterar o PEI de outro professor.")
            if pei.status not in self.STATUS_AGUARDANDO_NOVA_VERSAO:
                raise TransicaoPeiInvalida(
                    "Só é possível enviar uma nova versão de um PEI devolvido ou com ajustes solicitados."
                )

            ultima = pei.versao_atual
            versao = VersaoPei.objects.create(
                pei=pei,
                numero=(ultima.numero if ultima else 0) + 1,
                arquivo=arquivo,
                enviado_por=professor,
                comentario=comentario,
            )
            pei.arquivo = versao.arquivo.name
            pei.save(update_fields=["arquivo"])
            historico = pei._registrar_mudanca(self.EM_ANALISE, professor, comentario, versao=versao)

        self.arquivo = versao.arquivo.name
        self.status = self.EM_ANALISE
        return historico

    def _registrar_mudanca(self, novo_status, autor, observacao="", versao=None):
        status_anterior = self.status
        self.status = novo_status
        self.save(update_fields=["status"])
        return HistoricoPei.objects.create(
            pei=self,
            status_anterior=status_anterior,
            status_novo=novo_status,
            alterado_por=autor,
            observacao=observacao,
            versao=versao or self.versao_atual,
        )

    def _notificar_professor_da_analise(self, novo_status, remetente):
        textos = {
            self.ANALISADO: (
                "PEI analisado",
                "O NAPNE concluiu a análise do seu PEI nº {numero}, enviado em {data}. Abra o PEI para ler o parecer.",
            ),
            self.DEVOLVIDO: (
                "PEI devolvido",
                "O NAPNE devolveu o seu PEI nº {numero}, enviado em {data}. Abra o PEI para ler o parecer e enviar uma nova versão.",
            ),
            self.AJUSTES_SOLICITADOS: (
                "Ajustes solicitados no PEI",
                "O NAPNE solicitou ajustes no seu PEI nº {numero}, enviado em {data}. Abra o PEI para ler o parecer e enviar uma nova versão.",
            ),
        }
        cabecalho, corpo = textos[novo_status]
        Notificacao.objects.create(
            titulo=f"{cabecalho} (nº {self.id})",
            conteudo=corpo.format(numero=self.id, data=self.data_envio.strftime("%d/%m/%Y")),
            destino_tipo=Notificacao.USUARIO,
            destinatario=self.professor,
            remetente=remetente,
            link=reverse("detalhar_meu_pei", args=[self.id]),
        )


class VersaoPei(models.Model):
    pei = models.ForeignKey(Pei, on_delete=models.CASCADE, related_name="versoes")
    numero = models.PositiveIntegerField()
    arquivo = models.FileField(upload_to=caminho_arquivo_pei, storage=armazenamento_privado_pei)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True)

    class Meta:
        ordering = ["numero"]
        constraints = [
            models.UniqueConstraint(fields=["pei", "numero"], name="unique_numero_de_versao_por_pei"),
        ]

    def nome_do_download(self):
        extensao = os.path.splitext(self.arquivo.name)[1].lower()
        return f"PEI-{self.pei_id}-v{self.numero}{extensao}"

    def __str__(self):
        return f"{self.pei.titulo} (versão {self.numero})"


class HistoricoPei(models.Model):
    pei = models.ForeignKey(Pei, on_delete=models.CASCADE, related_name="historico")
    status_anterior = models.CharField(max_length=20, choices=Pei.STATUS_CHOICES)
    status_novo = models.CharField(max_length=20, choices=Pei.STATUS_CHOICES)
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    observacao = models.TextField(blank=True)  # parecer do NAPNE ou comentário do professor
    alterado_em = models.DateTimeField(auto_now_add=True)
    versao = models.ForeignKey(
        VersaoPei, on_delete=models.SET_NULL, null=True, blank=True, related_name="historico"
    )

    class Meta:
        ordering = ["alterado_em", "id"]

    def badge_anterior_theme(self):
        return Pei.STATUS_BADGE.get(self.status_anterior, "secondary")

    def badge_novo_theme(self):
        return Pei.STATUS_BADGE.get(self.status_novo, "secondary")

    def descricao_evento(self):
        if self.status_novo == Pei.EM_ANALISE:
            if self.status_anterior in Pei.STATUS_AGUARDANDO_NOVA_VERSAO:
                return "Nova versão enviada pelo professor"
            return "Registro inicial"
        return {
            Pei.ANALISADO: "Análise concluída pelo NAPNE",
            Pei.DEVOLVIDO: "PEI devolvido pelo NAPNE",
            Pei.AJUSTES_SOLICITADOS: "Ajustes solicitados pelo NAPNE",
        }.get(self.status_novo, "Status alterado")

    def __str__(self):
        return f"{self.pei.titulo}: {self.status_anterior} → {self.status_novo}"
    
class RegistroAcessoPei(models.Model):
    VISUALIZOU = "visualizou"
    BAIXOU = "baixou"
    ACAO_CHOICES = [
        (VISUALIZOU, "Visualizou o PEI"),
        (BAIXOU, "Baixou o arquivo"),
    ]

    pei_id = models.PositiveIntegerField("PEI nº", db_index=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    acao = models.CharField("Ação", max_length=12, choices=ACAO_CHOICES)
    versao_numero = models.PositiveIntegerField("Versão", null=True, blank=True)
    criado_em = models.DateTimeField("Quando", auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "registro de acesso a PEI"
        verbose_name_plural = "registros de acesso a PEIs"

    @classmethod
    def registrar(cls, usuario, pei, acao, versao=None):
        return cls.objects.create(
            pei_id=pei.id,
            usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
            acao=acao,
            versao_numero=versao.numero if versao else None,
        )

    def __str__(self):
        return f"PEI nº {self.pei_id}: {self.get_acao_display()}"


def _apagar_arquivo_se_ninguem_usa(storage, nome):
    if not nome:
        return
    if Pei.objects.filter(arquivo=nome).exists() or VersaoPei.objects.filter(arquivo=nome).exists():
        return
    storage.delete(nome)


@receiver(post_delete, sender=VersaoPei)
@receiver(post_delete, sender=Pei)
def apagar_arquivos_ao_excluir(sender, instance, **kwargs):
    storage = instance.arquivo.storage
    nome = instance.arquivo.name
    transaction.on_commit(lambda: _apagar_arquivo_se_ninguem_usa(storage, nome))

class SolicitacaoNapne(models.Model):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    RECUSADO = "recusado"
    STATUS_CHOICES = [
        (PENDENTE, "Pendente"),
        (APROVADO, "Aprovado"),
        (RECUSADO, "Recusado"),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitacao_napne")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDENTE)
    criado_em = models.DateTimeField(auto_now_add=True)
    avaliado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="solicitacoes_napne_avaliadas")
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_status_display()})"


class FeedbackPublico(models.Model):
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='comentarios')
    conteudo = models.TextField(max_length = 500)
    data = models.DateField(auto_now_add = True)
    editado_em =models.DateTimeField(blank=True, null=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Comentário de {self.autor} na notícia {self.noticia}"

class FeedbackPrivado(models.Model):
    noticia = models.ForeignKey(Noticia, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks_privados')
    conteudo = models.TextField(max_length=500)
    data = models.DateField(auto_now_add=True)
    editado_em =models.DateTimeField(blank=True, null=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Feedback privado de {self.autor}"
    
class ApresentacaoNapne(models.Model):
    titulo = models.CharField(max_length=200, default="Conheça o NAPNE")
    conteudo = CKEditor5Field("Conteúdo", config_name="default", default="", blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.titulo
    
    @classmethod
    def obter_instancia(cls):
        apresentacao = cls.objects.first()
        if apresentacao is None:
            apresentacao = cls.objects.create()
        return apresentacao
    
class Notificacao(models.Model):
    TODOS = "todos"
    PROFESSORES = "professores"
    ALUNOS = "alunos"
    NAPNE = "napne"
    USUARIO = "usuario"

    DESTINO_CHOICES = [
        (TODOS, "Todos os usuários"),
        (PROFESSORES, "Todos os professores"),
        (ALUNOS, "Todos os alunos"),
        (NAPNE, "Todos os membros do NAPNE"),
        (USUARIO, "Um usuário específico"),
    ]

    GRUPO_POR_DESTINO = {
        PROFESSORES: "Servidor",
        ALUNOS: "Estudante",
        NAPNE: "NAPNE",
    }

    titulo = models.CharField(max_length=100)
    conteudo = models.TextField()
    destino_tipo = models.CharField(max_length=20, choices=DESTINO_CHOICES, default=TODOS)
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificacoes_recebidas",
    )
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notificacoes_enviadas",
    )
    lida_por = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="notificacoes_lidas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    link = models.CharField(
        max_length=255,
        blank=True,
        help_text="Caminho interno para onde a notificação leva (ex.: /meus-peis/3/). Preenchido pelo sistema.",
    )

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.titulo} ({self.get_destino_tipo_display()})"

    def destinatarios_possiveis(self):
        """
        Devolve o QuerySet de usuários que podem ver esta notificação,
        de acordo com o destino_tipo escolhido.
        """
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()

        if self.destino_tipo == self.USUARIO:
            if self.destinatario_id:
                return UserModel.objects.filter(id=self.destinatario_id)
            return UserModel.objects.none()

        if self.destino_tipo == self.TODOS:
            return UserModel.objects.all()

        nome_grupo = self.GRUPO_POR_DESTINO.get(self.destino_tipo)
        if nome_grupo:
            return UserModel.objects.filter(groups__name=nome_grupo)

        return UserModel.objects.none()

    def visivel_para(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.destinatarios_possiveis().filter(id=user.id).exists()

    @classmethod
    def para_usuario(cls, user):
        if not user or not user.is_authenticated:
            return cls.objects.none()

        grupos_do_usuario = list(user.groups.values_list("name", flat=True))

        filtro = Q(destino_tipo=cls.TODOS) | Q(destino_tipo=cls.USUARIO, destinatario=user)

        for destino, nome_grupo in cls.GRUPO_POR_DESTINO.items():
            if nome_grupo in grupos_do_usuario:
                filtro |= Q(destino_tipo=destino)

        return cls.objects.filter(filtro).distinct()
    
    @classmethod
    def nao_lidas_para(cls, user):
        if not user or not user.is_authenticated:
            return cls.objects.none()
        return cls.para_usuario(user).exclude(lida_por=user)


class ImagemCarrossel(models.Model):
    apresentacao = models.ForeignKey(ApresentacaoNapne, on_delete=models.CASCADE, related_name="imagens")
    imagem = models.ImageField(upload_to="apresentacao_napne")
    legenda = models.CharField(max_length=200, blank=True)
    ordem = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["ordem", "id"]
    
    def __str__(self):
        return self.legenda or f"imagem #{self.pk}"
