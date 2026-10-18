import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class ArmazenamentoPrivado(FileSystemStorage):
    """
    Guarda arquivos fora da pasta pública (MEDIA_ROOT), em settings.PEI_ARMAZENAMENTO_PRIVADO.

    Não existe URL pública para esses arquivos: o único caminho até eles são as views, que
    conferem o perfil de quem pede (professor dono do PEI ou NAPNE).
    """

    @property
    def base_location(self):
        return settings.PEI_ARMAZENAMENTO_PRIVADO

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Arquivos de PEI são privados e não têm URL pública; use o download pela view.")


def armazenamento_privado_pei():
    return ArmazenamentoPrivado()
