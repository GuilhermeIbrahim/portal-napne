import os

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Pei, VersaoPei


class Command(BaseCommand):
    help = (
        "Lista (e, com --apagar, remove) arquivos de PEI que não pertencem a nenhum PEI: sobras de "
        "exclusões feitas antes de o sistema apagar os arquivos junto. Procura na área privada e na "
        "pasta pública antiga (MEDIA_ROOT/pei). Sem --apagar, só mostra o que encontrou."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apagar", action="store_true", help="Remove de verdade os arquivos órfãos.")

    def handle(self, *args, **opcoes):
        em_uso = set(Pei.objects.exclude(arquivo="").values_list("arquivo", flat=True))
        em_uso |= set(VersaoPei.objects.exclude(arquivo="").values_list("arquivo", flat=True))

        orfaos = []
        for raiz in (settings.PEI_ARMAZENAMENTO_PRIVADO, settings.MEDIA_ROOT):
            pasta = os.path.join(str(raiz), "pei")
            if not os.path.isdir(pasta):
                continue
            for nome in sorted(os.listdir(pasta)):
                caminho = os.path.join(pasta, nome)
                if os.path.isfile(caminho) and f"pei/{nome}" not in em_uso:
                    orfaos.append(caminho)

        if not orfaos:
            self.stdout.write(self.style.SUCCESS("Nenhum arquivo órfão encontrado."))
            return

        for caminho in orfaos:
            if opcoes["apagar"]:
                os.remove(caminho)
                self.stdout.write(f"Apagado: {caminho}")
            else:
                self.stdout.write(f"Órfão: {caminho}")

        if opcoes["apagar"]:
            self.stdout.write(self.style.SUCCESS(f"{len(orfaos)} arquivo(s) apagado(s)."))
        else:
            self.stdout.write(self.style.WARNING(
                f"{len(orfaos)} arquivo(s) órfão(s). Confira a lista e rode de novo com --apagar para removê-los."
            ))
