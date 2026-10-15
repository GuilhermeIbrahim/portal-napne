import os

from django.http import FileResponse, Http404


def resposta_de_download(arquivo):
    if not arquivo:
        raise Http404("Este PEI não tem arquivo.")

    try:
        arquivo.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404("O arquivo não foi encontrado no servidor.")

    return FileResponse(arquivo, as_attachment=True, filename=os.path.basename(arquivo.name))
