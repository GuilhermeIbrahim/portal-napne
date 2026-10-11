from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django_ckeditor_5.fields import CKEditor5Field
from django.urls import reverse


class Usuario(AbstractUser):
    pass

class Noticia(models.Model):
    titulo = models.CharField(max_length=100)
    imagem = models.ImageField(upload_to="Noticias", null=True, blank=True)
    data = models.DateField(auto_now_add=True)
    conteudo = CKEditor5Field("Conteúdo", config_name="default")

    def __str__(self):
        return self.titulo

class Pei(models.Model):
    titulo = models.CharField(max_length= 100) 
    arquivo = models.FileField(upload_to="pei")
    data_envio = models.DateField(auto_now_add=True)
    professor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    EM_ANALISE = "em_analise"
    ANALISADO = "analizado"
    DEVOLVIDO = "devolvido"

    STATUS_CHOICES = [
        (EM_ANALISE, "Em análise"),
        (ANALISADO, "Analisado"),
        (DEVOLVIDO, "Devolvido"),
    ]

    STATUS_BADGE = {
        EM_ANALISE : "warning",
        ANALISADO : "success",
        DEVOLVIDO : "danger",
    }

    def badge_theme(self):
        return self.STATUS_BADGE.get(self.status, "secondary")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=EM_ANALISE)

    def __str__(self):
        return self.titulo 

    def alterar_status(self, novo_status, alterado_por, observacao="", request=None):
        if novo_status == self.status:
            return None

        status_anterior = self.status
        self.status = novo_status
        self.save(update_fields=["status"])

        historico = HistoricoPei.objects.create(
            pei=self,
            status_anterior=status_anterior,
            status_novo=novo_status,
            alterado_por=alterado_por,
            observacao=observacao,
        )

        caminho_pei = reverse("detalhar_meu_pei", args=[self.id])
        link_pei = request.build_absolute_uri(caminho_pei) if request else caminho_pei

        Notificacao.objects.create(
            titulo=f"O status do PEI '{self.titulo}' foi alterado para '{self.get_status_display()}'",
            conteudo=(
                f"O status do PEI '{self.titulo}' foi alterado para "
                f"'{self.get_status_display()}'. Acesse: {link_pei}"
            ),
            destino_tipo=Notificacao.USUARIO,
            destinatario=self.professor,
            remetente=alterado_por,
        )

        return historico

class HistoricoPei(models.Model):
    pei = models.ForeignKey(Pei, on_delete=models.CASCADE, related_name="historico")
    status_anterior = models.CharField(max_length=20, choices=Pei.STATUS_CHOICES)
    status_novo = models.CharField(max_length=20, choices=Pei.STATUS_CHOICES)
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,)
    observacao = models.TextField(blank=True)
    alterado_em = models.DateTimeField(auto_now_add=True)

    def badge_anterior_theme(self):
        return Pei.STATUS_BADGE.get(self.status_anterior, "secondary")

    def badge_novo_theme(self):
        return Pei.STATUS_BADGE.get(self.status_novo, "secondary")

    class Meta:
        ordering = ["alterado_em"]

    def __str__(self):
        return f"{self.pei.titulo}: {self.status_anterior} → {self.status_novo}"
    
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
