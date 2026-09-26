from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


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

    def __str__(self):
        return self.titulo 
    
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
    
class ImagemCarrossel(models.Model):
    apresentacao = models.ForeignKey(ApresentacaoNapne, on_delete=models.CASCADE, related_name="imagens")
    imagem = models.ImageField(upload_to="apresentacao_napne")
    legenda = models.CharField(max_length=200, blank=True)
    ordem = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["ordem", "id"]
    
    def __str__(self):
        return self.legenda or f"imagem #{self.pk}"