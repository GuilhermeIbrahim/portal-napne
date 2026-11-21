import io
import os
import zipfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from .forms import NovaVersaoPeiForm, PeiForm
from .models import Pei
from .tests import BaseTestes

MB = 1024 * 1024

DADOS_DO_PEI = {
    'titulo': 'PEI de Matemática - 7º ano',
    'estudante_nome': 'Joana Pereira de Souza',
    'estudante_matricula': '20231012345678',
    'estudante_curso': 'Técnico em Informática',
    'periodo_letivo': '2026.1',
}


def pdf(nome='pei.pdf', tamanho=None):
    conteudo = b'%PDF-1.4 conteudo de teste'
    if tamanho:
        conteudo = conteudo.ljust(tamanho, b' ')
    return SimpleUploadedFile(nome, conteudo, content_type='application/pdf')


def docx(nome='pei.docx', tamanho=None, com_documento=True):
    """Monta um .docx de verdade (pacote ZIP). Com `tamanho`, adiciona um anexo sem compressão para ficar perto desse tamanho."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, 'w', zipfile.ZIP_STORED) as pacote:
        pacote.writestr('[Content_Types].xml', '<Types/>')
        if com_documento:
            pacote.writestr('word/document.xml', '<w:document/>')
        if tamanho:
            pacote.writestr('word/media/anexo.bin', os.urandom(tamanho - 1000))
    return SimpleUploadedFile(
        nome, memoria.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


def arquivos_gravados():
    achados = set()
    for raiz in (settings.MEDIA_ROOT, settings.PEI_ARMAZENAMENTO_PRIVADO):
        for pasta, _, nomes in os.walk(raiz):
            achados.update(os.path.join(pasta, nome) for nome in nomes)
    return achados


def formulario_de_envio(arquivo):
    return PeiForm(data=DADOS_DO_PEI, files={'arquivo': arquivo} if arquivo else {})


def erros_do_arquivo(form):
    return form.errors.get('arquivo', [])


# ---------------------------------------------------------------------------------------
class TiposAceitosTests(BaseTestes):
    def test_pdf_valido_e_aceito(self):
        form = formulario_de_envio(pdf())
        self.assertTrue(form.is_valid(), form.errors)

    def test_docx_valido_e_aceito(self):
        form = formulario_de_envio(docx())
        self.assertTrue(form.is_valid(), form.errors)

    def test_extensao_em_maiusculas_e_aceita(self):
        for arquivo in (pdf('PEI.PDF'), docx('PEI.DOCX')):
            with self.subTest(nome=arquivo.name):
                self.assertTrue(formulario_de_envio(arquivo).is_valid())

    def test_arquivo_continua_legivel_do_comeco_depois_da_validacao(self):
        form = formulario_de_envio(pdf())
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['arquivo'].read(5), b'%PDF-')

    def test_docx_grande_chega_em_arquivo_temporario_e_tambem_e_aceito(self):
        self.client.force_login(self.professor)
        resposta = self.client.post(
            reverse('enviar_pei'),
            {**DADOS_DO_PEI, 'arquivo': docx('grande.docx', tamanho=3 * MB)},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Pei.objects.filter(titulo=DADOS_DO_PEI['titulo']).exists())


class TamanhoTests(BaseTestes):
    def test_arquivo_de_exatamente_10_mb_e_aceito(self):
        self.assertTrue(formulario_de_envio(pdf(tamanho=10 * MB)).is_valid())

    def test_arquivo_de_10_mb_mais_1_byte_e_rejeitado_dizendo_tamanho_e_limite(self):
        form = formulario_de_envio(pdf(tamanho=10 * MB + 1))
        self.assertFalse(form.is_valid())
        mensagem = erros_do_arquivo(form)[0]
        self.assertIn('10,1 MB', mensagem)
        self.assertIn('limite é de 10 MB', mensagem)

    def test_mensagem_mostra_o_tamanho_real_do_arquivo(self):
        form = formulario_de_envio(pdf(tamanho=12 * MB + MB // 2))
        self.assertIn('12,5 MB', erros_do_arquivo(form)[0])

    def test_o_limite_vem_de_uma_unica_configuracao(self):
        with override_settings(PEI_TAMANHO_MAXIMO_MB=1):
            self.assertTrue(formulario_de_envio(pdf(tamanho=MB)).is_valid())
            form = formulario_de_envio(pdf(tamanho=MB + 1))
            self.assertFalse(form.is_valid())
            self.assertIn('limite é de 1 MB', erros_do_arquivo(form)[0])

            self.assertIn('1 MB', PeiForm().fields['arquivo'].help_text)
            self.assertIn('1 MB', NovaVersaoPeiForm().fields['arquivo'].help_text)

    def test_texto_de_ajuda_dos_formularios_mostra_o_limite_padrao(self):
        for formulario in (PeiForm(), NovaVersaoPeiForm()):
            ajuda = formulario.fields['arquivo'].help_text
            self.assertIn('PDF ou DOCX', ajuda)
            self.assertIn('10 MB', ajuda)


class ExtensaoETipoTests(BaseTestes):
    def test_extensao_nao_permitida_e_rejeitada_mesmo_com_conteudo_de_pdf(self):
        for nome in ('pei.txt', 'pei.exe', 'pei.doc', 'pei.pdf.exe', 'pei'):
            with self.subTest(nome=nome):
                arquivo = SimpleUploadedFile(nome, b'%PDF-1.4 conteudo', content_type='application/pdf')
                form = formulario_de_envio(arquivo)
                self.assertFalse(form.is_valid())
                self.assertIn('Formato não permitido', erros_do_arquivo(form)[0])

    def test_nao_confia_no_content_type_informado_pelo_navegador(self):
        arquivo = SimpleUploadedFile('pei.pdf', b'MZ\x90\x00 programa', content_type='application/pdf')
        form = formulario_de_envio(arquivo)
        self.assertFalse(form.is_valid())
        self.assertIn('não é um PDF válido', erros_do_arquivo(form)[0])

    def test_pdf_com_conteudo_de_outro_tipo_e_rejeitado(self):
        for conteudo in (b'texto comum', docx().read(), b'\x89PNG\r\n\x1a\n'):
            with self.subTest(inicio=conteudo[:6]):
                form = formulario_de_envio(SimpleUploadedFile('pei.pdf', conteudo))
                self.assertFalse(form.is_valid())
                self.assertIn('não é um PDF válido', erros_do_arquivo(form)[0])

    def test_docx_com_conteudo_de_pdf_ou_texto_e_rejeitado(self):
        for conteudo in (b'%PDF-1.4 conteudo', b'texto comum'):
            with self.subTest(inicio=conteudo[:6]):
                form = formulario_de_envio(SimpleUploadedFile('pei.docx', conteudo))
                self.assertFalse(form.is_valid())
                self.assertIn('não é um Word (.docx) válido', erros_do_arquivo(form)[0])

    def test_zip_comum_renomeado_para_docx_e_rejeitado(self):
        form = formulario_de_envio(docx(com_documento=False))
        self.assertFalse(form.is_valid())
        self.assertIn('não é um Word (.docx) válido', erros_do_arquivo(form)[0])

    def test_docx_corrompido_cortado_no_meio_e_rejeitado(self):
        inteiro = docx().read()
        form = formulario_de_envio(SimpleUploadedFile('pei.docx', inteiro[: len(inteiro) // 2]))
        self.assertFalse(form.is_valid())
        self.assertIn('Word (.docx)', erros_do_arquivo(form)[0])


class ArquivoVazioOuAusenteTests(BaseTestes):
    def test_arquivo_vazio_e_rejeitado_com_mensagem_apropriada(self):
        for nome in ('pei.pdf', 'pei.docx'):
            with self.subTest(nome=nome):
                form = formulario_de_envio(SimpleUploadedFile(nome, b''))
                self.assertFalse(form.is_valid())
                self.assertIn('O arquivo está vazio', erros_do_arquivo(form)[0])

    def test_envio_sem_arquivo_pede_para_selecionar(self):
        form = formulario_de_envio(None)
        self.assertFalse(form.is_valid())
        self.assertEqual(erros_do_arquivo(form), ['Selecione o arquivo do PEI.'])

    def test_nova_versao_sem_arquivo_e_vazia_tambem_sao_rejeitadas(self):
        self.assertFalse(NovaVersaoPeiForm(data={}, files={}).is_valid())
        form = NovaVersaoPeiForm(data={}, files={'arquivo': SimpleUploadedFile('v2.pdf', b'')})
        self.assertFalse(form.is_valid())
        self.assertIn('O arquivo está vazio', erros_do_arquivo(form)[0])


# ---------------------------------------------------------------------------------------
class ValidacaoNasTelasTests(BaseTestes):
    def enviar(self, arquivo):
        return self.client.post(reverse('enviar_pei'), {**DADOS_DO_PEI, 'arquivo': arquivo})

    def test_envio_rejeitado_mostra_o_erro_nao_cria_pei_e_nao_grava_nada(self):
        self.client.force_login(self.professor)
        antes = arquivos_gravados()
        total = Pei.objects.count()

        resposta = self.enviar(SimpleUploadedFile('virus.pdf', b'MZ\x90\x00 programa', content_type='application/pdf'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'não é um PDF válido')
        self.assertEqual(Pei.objects.count(), total)
        self.assertEqual(arquivos_gravados(), antes)

    def test_envio_acima_do_limite_nao_deixa_residuo(self):
        self.client.force_login(self.professor)
        antes = arquivos_gravados()

        resposta = self.enviar(pdf('grande.pdf', tamanho=10 * MB + 1))

        self.assertContains(resposta, 'limite é de 10 MB')
        self.assertEqual(arquivos_gravados(), antes)

    def test_envio_valido_grava_exatamente_um_arquivo(self):
        self.client.force_login(self.professor)
        antes = arquivos_gravados()
        self.assertEqual(self.enviar(pdf('ok.pdf')).status_code, 302)
        self.assertEqual(len(arquivos_gravados() - antes), 1)

    def test_formulario_de_envio_mostra_o_limite_na_tela(self):
        self.client.force_login(self.professor)
        self.assertContains(self.client.get(reverse('enviar_pei')), 'PDF ou DOCX, com até 10 MB')

    def test_reenvio_rejeitado_mantem_o_pei_devolvido_e_nao_grava_nada(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Corrija o item 3.', self.napne)
        self.client.force_login(self.professor)
        antes = arquivos_gravados()

        resposta = self.client.post(
            reverse('reenviar_pei', args=[self.pei.id]),
            {'arquivo': SimpleUploadedFile('v2.pdf', b'texto comum'), 'comentario': 'x'},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'não é um PDF válido')
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.DEVOLVIDO)
        self.assertEqual(self.pei.versoes.count(), 1)
        self.assertEqual(arquivos_gravados(), antes)

    def test_reenvio_valido_continua_funcionando(self):
        self.pei.registrar_analise(Pei.DECISAO_DEVOLVER, 'Corrija o item 3.', self.napne)
        self.client.force_login(self.professor)

        resposta = self.client.post(reverse('reenviar_pei', args=[self.pei.id]), {'arquivo': docx('v2.docx')})

        self.assertEqual(resposta.status_code, 302)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.status, Pei.EM_ANALISE)
        self.assertEqual(self.pei.versoes.count(), 2)

    def test_edicao_pelo_painel_nunca_recebe_arquivo_nem_grava_nada(self):
        self.client.force_login(self.napne)
        antes = arquivos_gravados()
        arquivo_antes = self.pei.arquivo.name

        resposta = self.client.post(
            reverse('editar_pei', args=[self.pei.id]),
            {**DADOS_DO_PEI, 'arquivo': SimpleUploadedFile('intruso.exe', b'MZ\x90\x00')},
        )

        self.assertEqual(resposta.status_code, 302)
        self.pei.refresh_from_db()
        self.assertEqual(self.pei.arquivo.name, arquivo_antes)
        self.assertEqual(arquivos_gravados(), antes)
