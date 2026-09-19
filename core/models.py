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