import os
import re
import shutil
import uuid

from django.conf import settings
from django.db import migrations

NOME_JA_PRIVADO = re.compile(r"pei/[0-9a-f]{32}(\.[a-z0-9]{1,5})?")


def mover_para_area_privada(apps, schema_editor):
    Pei = apps.get_model('core', 'Pei')
    VersaoPei = apps.get_model('core', 'VersaoPei')

    raiz_publica = os.path.abspath(settings.MEDIA_ROOT)
    raiz_privada = os.path.abspath(settings.PEI_ARMAZENAMENTO_PRIVADO)

    nomes = set(Pei.objects.exclude(arquivo='').values_list('arquivo', flat=True))
    nomes |= set(VersaoPei.objects.exclude(arquivo='').values_list('arquivo', flat=True))

    for antigo in nomes:
        if NOME_JA_PRIVADO.fullmatch(antigo):
            continue

        origem = os.path.abspath(os.path.join(raiz_publica, antigo))
        if not origem.startswith(raiz_publica + os.sep) or not os.path.isfile(origem):
            continue  # nome estranho ou arquivo que já não está no disco: não mexe

        extensao = os.path.splitext(antigo)[1].lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,5}", extensao):
            extensao = ''
        novo = f"pei/{uuid.uuid4().hex}{extensao}"

        destino = os.path.join(raiz_privada, novo)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.move(origem, destino)

        Pei.objects.filter(arquivo=antigo).update(arquivo=novo)
        VersaoPei.objects.filter(arquivo=antigo).update(arquivo=novo)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_dados_do_estudante_e_arquivo_privado'),
    ]

    operations = [
        migrations.RunPython(mover_para_area_privada, migrations.RunPython.noop),
    ]
