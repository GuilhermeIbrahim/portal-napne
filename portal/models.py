<<<<<<< HEAD
=======
from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    pass

class FeedbackPublico(models.Model):
    titulo = models.CharField(max_length=50)
    conteudo = models.CharField(max_length = 200)
    data = models.DateField(auto_now_add = True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return self.titulo
    
class FeedbackPrivado(models.Model):
    titulo = models.CharField(max_length=50)
    conteudo = models.CharField(max_length=200)
    data = models.DateField(auto_now_add = True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return self.titulo
>>>>>>> c21c7da6615de4faf12ec6f9a9e962b187ad9d58
