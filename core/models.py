from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.contrib.auth.models import User


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
    professor = models.ForeignKey(User, on_delete=models.CASCADE)

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
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="solicitacao_napne")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDENTE)
    criado_em = models.DateTimeField(auto_now_add=True)
    avaliado_por = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="solicitacoes_napne_avaliadas")
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_status_display()})"