import math
import os
import re
import unicodedata
import zipfile
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError

PARTICULAS_DE_NOME = {"da", "de", "do", "das", "dos", "e"}
ANO_MINIMO = 2000

MENSAGEM_TITULO_REVELA_ESTUDANTE = (
    "O título não deve conter o nome nem a matrícula do estudante, pois ele aparece em listas e avisos. "
    "Use algo como \"PEI de Matemática - 2º ano\"."
)


def _espacos(texto):
    return " ".join((texto or "").split())


def sem_acentos(texto):
    decomposto = unicodedata.normalize("NFKD", texto or "")
    return "".join(letra for letra in decomposto if not unicodedata.combining(letra))


# ---------------------------------------------------------------------------------- nome
def normalizar_nome_estudante(valor):
    return _espacos(valor)


def validar_nome_estudante(valor):
    nome = normalizar_nome_estudante(valor)

    if not re.fullmatch(r"[^\W\d_]+(?:[ '.\-][^\W\d_]+)*\.?", nome):
        raise ValidationError("Use apenas letras, espaços, apóstrofo, ponto e hífen no nome do estudante.")

    if len(re.findall(r"[^\W\d_]+", nome)) < 2:
        raise ValidationError("Informe o nome completo do estudante (nome e sobrenome).")


# ----------------------------------------------------------------------------- matrícula
def normalizar_matricula(valor):
    """Aceita pontos, hífens e espaços na digitação e guarda só os números."""
    return re.sub(r"[\s.\-]", "", valor or "")


def validar_matricula(valor):
    if not re.fullmatch(r"\d{14}", normalizar_matricula(valor)):
        raise ValidationError("A matrícula deve ter apenas números, sendo 14 dígitos.")


# --------------------------------------------------------------------------------- curso
def normalizar_curso(valor):
    return _espacos(valor)


def validar_curso(valor):
    curso = normalizar_curso(valor)

    if not re.fullmatch(r"[\w\s.,()/&:'ºª°\-–]+", curso):
        raise ValidationError("O nome do curso tem caracteres que não são permitidos.")
    if len(re.findall(r"[^\W\d_]", curso)) < 3:
        raise ValidationError("Informe o nome do curso, por exemplo \"Técnico em Informática\".")


# ------------------------------------------------------------------------ período letivo
def normalizar_periodo_letivo(valor):
    """Aceita 2026.1, 2026/1, 2026-1 ou 2026 1 e guarda sempre como 2026.1."""
    texto = _espacos(valor)
    correspondencia = re.fullmatch(r"(\d{4})\s*[./\-]?\s*(\d)", texto)
    if correspondencia:
        return f"{correspondencia.group(1)}.{correspondencia.group(2)}"
    return texto


def validar_periodo_letivo(valor):
    correspondencia = re.fullmatch(r"(\d{4})\.([12])", valor or "")
    if not correspondencia:
        raise ValidationError("Use o formato ano.semestre, por exemplo 2026.1 ou 2026.2.")

    ano = int(correspondencia.group(1))
    ano_maximo = date.today().year + 1
    if not ANO_MINIMO <= ano <= ano_maximo:
        raise ValidationError(f"O ano do período letivo deve estar entre {ANO_MINIMO} e {ano_maximo}.")


# ------------------------------------------------------------------- título x estudante
def titulo_revela_o_estudante(titulo, nome, matricula=""):
    """
    True se o título do PEI contém o nome (qualquer parte de 3+ letras, como palavra inteira) ou a
    matrícula do estudante. O título aparece em listas, e-mails e telas compartilhadas; os dados
    do estudante têm campos próprios, com acesso controlado.
    """
    palavras_do_titulo = set(re.findall(r"[a-z0-9]+", sem_acentos(titulo).lower()))

    for parte in re.findall(r"[a-z]+", sem_acentos(nome).lower()):
        if len(parte) >= 3 and parte not in PARTICULAS_DE_NOME and parte in palavras_do_titulo:
            return True

    matricula = normalizar_matricula(matricula)
    if matricula and matricula in re.sub(r"[\s.\-]", "", titulo or ""):
        return True

    return False


BYTES_POR_MB = 1024 * 1024
EXTENSOES_DO_PEI = (".pdf", ".docx")


def _mb_para_exibir(tamanho_em_bytes):
    """Arredonda PARA CIMA com 1 casa (10 MB + 1 byte aparece como 10,1 MB, nunca como "10 MB" de novo)."""
    mb = math.ceil(tamanho_em_bytes / BYTES_POR_MB * 10) / 10
    return f"{mb:.1f}".replace(".", ",")


def _parece_pdf(arquivo):
    return arquivo.read(5) == b"%PDF-"


def _parece_docx(arquivo):
    try:
        with zipfile.ZipFile(arquivo) as pacote:
            nomes = set(pacote.namelist())
    except (zipfile.BadZipFile, OSError, EOFError, ValueError):
        return False
    return "[Content_Types].xml" in nomes and "word/document.xml" in nomes


def validar_arquivo_pei(arquivo):
    """
    Valida no servidor um arquivo de PEI: tamanho, extensão e conteúdo real (PDF ou DOCX).
    Não confia no atributo accept do navegador nem no content_type informado pelo cliente.
    """
    limite_mb = settings.PEI_TAMANHO_MAXIMO_MB
    tamanho = arquivo.size

    if tamanho == 0:
        raise ValidationError("O arquivo está vazio. Selecione o arquivo correto do PEI.")

    if tamanho > limite_mb * BYTES_POR_MB:
        raise ValidationError(
            f"O arquivo tem {_mb_para_exibir(tamanho)} MB, mas o limite é de {limite_mb} MB. "
            "Reduza o tamanho do arquivo e envie novamente."
        )

    extensao = os.path.splitext(arquivo.name or "")[1].lower()
    if extensao not in EXTENSOES_DO_PEI:
        raise ValidationError("Formato não permitido. Envie um arquivo PDF (.pdf) ou Word (.docx).")

    arquivo.seek(0)
    try:
        conteudo_confere = _parece_pdf(arquivo) if extensao == ".pdf" else _parece_docx(arquivo)
    finally:
        arquivo.seek(0) 

    if not conteudo_confere:
        tipo = "PDF" if extensao == ".pdf" else "Word (.docx)"
        raise ValidationError(
            f"O conteúdo do arquivo não é um {tipo} válido. Ele pode estar corrompido ou ter sido "
            f"renomeado a partir de outro formato. Abra o arquivo, salve-o como {tipo} e tente novamente."
        )
