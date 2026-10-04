from django.apps import AppConfig
from django.db.models.signals import post_migrate

NOMES_DOS_GRUPOS = ("NAPNE", "Estudante", "Servidor")

def criar_grupos_de_perfil(sender, using="default", **kwargs):
    from django.contrib.auth.models import Group
    
    for nome in NOMES_DOS_GRUPOS:
        Group.objects.using(using).get_or_create(name=nome)

class CoreConfig(AppConfig):
    name = 'core'
    
    def ready(self):
        post_migrate.connect(
            criar_grupos_de_perfil,
            sender=self,
            dispatch_uid="core.criar_grupos_de_perfil",
        )
