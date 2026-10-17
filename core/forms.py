from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.forms import inlineformset_factory

from .models import (
    ApresentacaoNapne,
    FeedbackPrivado,
    FeedbackPublico,
    ImagemCarrossel,
    Noticia,
    Notificacao,
    Pei,
)

from .validators import (
    MENSAGEM_TITULO_REVELA_ESTUDANTE,
    normalizar_curso,
    normalizar_matricula,
    normalizar_nome_estudante,
    normalizar_periodo_letivo,
    titulo_revela_o_estudante,
    validar_curso,
    validar_matricula,
    validar_nome_estudante,
    validar_periodo_letivo,
)


class NoticiaForm(forms.ModelForm):
    class Meta:
        model = Noticia
        fields = ["titulo", "imagem", "conteudo"]
        labels = {
            "titulo": "Título",
            "imagem": "Imagem de capa",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Título da notícia"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("titulo"),
            Field("imagem"),
            HTML("<label class='form-label mt-2'>Conteúdo</label>"),
            Div(Field("conteudo"), css_class="mb-3"),
        )

CAMPOS_DO_ESTUDANTE = ["estudante_nome", "estudante_matricula", "estudante_curso", "periodo_letivo"]

class DadosDoEstudanteMixin:
    AJUDA_NAO_ESCREVER_SAUDE = "Não escreva diagnóstico, laudo nem outras informações de saúde aqui."

    def configurar_campos_do_estudante(self):
        configuracao = {
            "estudante_nome": dict(
                label="Nome completo do estudante",
                help_text="Nome e sobrenome. " + self.AJUDA_NAO_ESCREVER_SAUDE,
                placeholder="Ex.: Maria da Silva Souza",
                autocomplete="off",
            ),
            "estudante_matricula": dict(
                label="Matrícula do estudante",
                help_text="14 números. Pontos e hífens digitados são removidos.",
                placeholder="Ex.: 20231012345678",
                autocomplete="off",
                inputmode="numeric",
            ),
            "estudante_curso": dict(
                label="Curso do estudante",
                help_text="Ex.: Técnico em Informática integrado ao Ensino Médio.",
                placeholder="Nome do curso",
                autocomplete="off",
            ),
            "periodo_letivo": dict(
                label="Período letivo",
                help_text="Formato ano.semestre, por exemplo 2026.1 ou 2026.2.",
                placeholder="2026.1",
                autocomplete="off",
                inputmode="decimal",
            ),
        }
        for nome, dados in configuracao.items():
            campo = self.fields[nome]
            campo.required = True
            campo.label = dados["label"]
            campo.help_text = dados["help_text"]
            campo.error_messages["required"] = f"Informe {self._artigo(nome)} {dados['label'].lower()}."
            campo.widget.attrs.update({
                "placeholder": dados["placeholder"],
                "autocomplete": dados["autocomplete"],
            })
            if "inputmode" in dados:
                campo.widget.attrs["inputmode"] = dados["inputmode"]

    @staticmethod
    def _artigo(nome_do_campo):
        return "a" if nome_do_campo == "estudante_matricula" else "o"

    def clean_estudante_nome(self):
        valor = normalizar_nome_estudante(self.cleaned_data["estudante_nome"])
        validar_nome_estudante(valor)
        return valor

    def clean_estudante_matricula(self):
        valor = normalizar_matricula(self.cleaned_data["estudante_matricula"])
        validar_matricula(valor)
        return valor

    def clean_estudante_curso(self):
        valor = normalizar_curso(self.cleaned_data["estudante_curso"])
        validar_curso(valor)
        return valor

    def clean_periodo_letivo(self):
        valor = normalizar_periodo_letivo(self.cleaned_data["periodo_letivo"])
        validar_periodo_letivo(valor)
        return valor

    def clean(self):
        dados = super().clean()
        titulo = dados.get("titulo")
        nome = dados.get("estudante_nome")
        matricula = dados.get("estudante_matricula", "")

        if titulo and nome and titulo_revela_o_estudante(titulo, nome, matricula):
            self.add_error("titulo", MENSAGEM_TITULO_REVELA_ESTUDANTE)
        return dados


class PeiForm(DadosDoEstudanteMixin, forms.ModelForm):
    class Meta:
        model = Pei
        fields = ["titulo", *CAMPOS_DO_ESTUDANTE, "arquivo"]
        labels = {
            "titulo": "Título do PEI",
            "arquivo": "Arquivo do PEI (PDF ou DOCX)",
        }
        help_texts = {
            "titulo": "Não use o nome do estudante. Ex.: \"PEI de Matemática - 7º ano\".",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Título do PEI"}),
            "arquivo": forms.ClearableFileInput(attrs={"accept": ".pdf, .docx"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurar_campos_do_estudante()

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<h2 class="h6 secao-formulario">Identificação do estudante</h2>'),
            HTML('{% include "portal/partials/_aviso_privacidade_pei.html" %}'),
            Field("estudante_nome"),
            Row(
                Column(Field("estudante_matricula"), css_class="col-md-6"),
                Column(Field("periodo_letivo"), css_class="col-md-6"),
            ),
            Field("estudante_curso"),
            HTML('<h2 class="h6 secao-formulario">Documento</h2>'),
            Field("titulo"),
            Field("arquivo"),
        )


class EditarPeiForm(DadosDoEstudanteMixin, forms.ModelForm):
    class Meta:
        model = Pei
        fields = ["titulo", *CAMPOS_DO_ESTUDANTE]
        labels = {"titulo": "Título do PEI"}
        help_texts = {"titulo": "Não use o nome do estudante."}
        widgets = {"titulo": forms.TextInput(attrs={"placeholder": "Título do PEI"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurar_campos_do_estudante()

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("estudante_nome"),
            Row(
                Column(Field("estudante_matricula"), css_class="col-md-6"),
                Column(Field("periodo_letivo"), css_class="col-md-6"),
            ),
            Field("estudante_curso"),
            Field("titulo"),
        )

class AnalisePeiForm(forms.Form):
    PARECER_MAX = 2000

    decisao = forms.ChoiceField(
        label="Decisão",
        choices=[
            (Pei.DECISAO_APROVAR, "Aprovar — o PEI fica como \"Analisado\""),
            (Pei.DECISAO_DEVOLVER, "Devolver ao professor"),
            (Pei.DECISAO_AJUSTES, "Solicitar ajustes ao professor"),
        ],
        widget=forms.RadioSelect,
        error_messages={
            "required": "Escolha uma decisão: aprovar, devolver ou solicitar ajustes.",
            "invalid_choice": "Escolha uma das decisões da lista.",
        },
    )
    parecer = forms.CharField(
        label="Parecer",
        required=False,
        max_length=PARECER_MAX,
        help_text="Obrigatório ao devolver ou solicitar ajustes; opcional ao aprovar. O professor lê este texto no PEI.",
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "Explique a decisão e, se for o caso, o que precisa ser corrigido",
            "data-obrigatorio-para": ",".join(Pei.DECISOES_QUE_EXIGEM_PARECER),
        }),
        error_messages={"max_length": f"O parecer pode ter no máximo {PARECER_MAX} caracteres."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(Field("decisao"), Field("parecer"))

    def clean(self):
        dados = super().clean()
        decisao = dados.get("decisao")
        parecer = (dados.get("parecer") or "").strip()

        if decisao in Pei.DECISOES_QUE_EXIGEM_PARECER and not parecer:
            self.add_error("parecer", "O parecer é obrigatório ao devolver ou solicitar ajustes.")

        dados["parecer"] = parecer
        return dados


class NovaVersaoPeiForm(forms.Form):
    arquivo = forms.FileField(
        label="Novo arquivo do PEI (PDF ou DOCX)",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf, .docx"}),
        error_messages={"required": "Selecione o arquivo corrigido do PEI."},
    )
    comentario = forms.CharField(
        label="Comentário para o NAPNE (opcional)",
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Descreva o que foi corrigido, se quiser"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(Field("arquivo"), Field("comentario"))


class CadastroNapneForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Ex.: Maria", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Ex.: da Silva", "autocomplete": "family-name"}),
    )
    email = forms.EmailField(
        label="E-mail",
        help_text="Use um e-mail que você acessa com frequência.",
        widget=forms.EmailInput(attrs={"placeholder": "nome@exemplo.com", "autocomplete": "email"}),
    )

    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email", "username", "password1", "password2"]
        labels = {"username": "Nome de usuário"}
        help_texts = {
            "username": "Será usado para entrar no portal. Use letras, números e os símbolos @ . + - _ (sem espaços).",
        }
        error_messages = {
            "username": {
                "unique": "Este nome de usuário já está em uso. Escolha outro.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "placeholder": "Ex.: maria.silva",
            "autocomplete": "username",
        })

        self.fields["password1"].label = "Senha"
        self.fields["password1"].help_text = ""  # as regras aparecem no quadro abaixo do campo
        self.fields["password1"].widget.attrs.update({
            "placeholder": "Crie uma senha",
            "autocomplete": "new-password",
            "data-mostrar-senha": "true",
            "data-regras-senha": "#regras-senha",
        })

        self.fields["password2"].label = "Confirme a senha"
        self.fields["password2"].help_text = "Digite a mesma senha novamente."
        self.fields["password2"].widget.attrs.update({
            "placeholder": "Repita a senha",
            "autocomplete": "new-password",
            "data-mostrar-senha": "true",
        })

        self.error_messages["password_mismatch"] = "As duas senhas não são iguais. Digite novamente."

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<h2 class="h6 secao-formulario">Seus dados</h2>'),
            Row(
                Column(Field("first_name"), css_class="col-md-6"),
                Column(Field("last_name"), css_class="col-md-6"),
            ),
            Field("email"),
            HTML('<h2 class="h6 secao-formulario">Seu acesso</h2>'),
            Field("username"),
            Field("password1"),
            HTML('{% include "portal/partials/_regras_senha.html" %}'),
            Field("password2"),
        )


class LoginNapneForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.error_messages["invalid_login"] = "Usuário ou senha incorretos. Confira os dados e tente novamente."
        self.error_messages["inactive"] = "Esta conta está inativa."

        self.fields["username"].label = "Nome de usuário"
        self.fields["username"].widget.attrs.update({
            "placeholder": "Seu nome de usuário",
            "autocomplete": "username",
            "autofocus": True,
        })
        self.fields["password"].label = "Senha"
        self.fields["password"].widget.attrs.update({
            "placeholder": "Sua senha",
            "autocomplete": "current-password",
            "data-mostrar-senha": "true",
        })

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("username"),
            Field("password"),
        )

class FeedbackPublicoForm(forms.ModelForm):
    class Meta:
        model = FeedbackPublico
        fields = ["conteudo"]
        labels = {"conteudo": "Comentário"}
        widgets = {
            "conteudo": forms.Textarea(attrs={"placeholder": "Escreva seu comentário aqui...", "rows": 3}),
        }

class FeedbackPrivadoForm(forms.ModelForm):  
    noticia = forms.ModelChoiceField(queryset=Noticia.objects.all(), widget=forms.HiddenInput(), required=False)
    class Meta:
        model = FeedbackPrivado
        fields = ["noticia", "conteudo"]
        labels = {"conteudo": "Mensagem"}
        widgets = {
            "conteudo": forms.Textarea(attrs={"placeholder": "Escreva seu feedback aqui...", "rows": 3}),
        }
        
class ApresentacaoNapneForm(forms.ModelForm):
    class Meta:
        model = ApresentacaoNapne
        fields = ["titulo", "conteudo"]
        labels = {"titulo": "Título"}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("titulo"),
            HTML("<label class='form-label mt-2'>Conteúdo</label>"),
            Div(Field("conteudo"), css_class="mb-3"),
        )
    
ImagemCarrosselFormSet = inlineformset_factory(
        ApresentacaoNapne,
        ImagemCarrossel,
        fields=["imagem", "legenda", "ordem"],
        labels={"imagem": "Imagem", "legenda": "Legenda", "ordem": "Ordem de exibição"},
        extra=3,
        can_delete=True,
)


class NotificacaoForm(forms.ModelForm):
    class Meta:
        model = Notificacao
        fields = ["titulo", "conteudo", "destino_tipo", "destinatario"]
        labels = {
            "titulo": "Título",
            "conteudo": "Mensagem",
            "destino_tipo": "Enviar para",
            "destinatario": "Usuário específico",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Título da notificação"}),
            "conteudo": forms.Textarea(attrs={"rows": 4, "placeholder": "Escreva a mensagem..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["destinatario"].queryset = get_user_model().objects.all().order_by("first_name", "username")
        self.fields["destinatario"].required = False

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("titulo"),
            Field("destino_tipo", css_id="id_destino_tipo"),
            Div(Field("destinatario"), css_id="div_destinatario"),
            Field("conteudo"),
        )

    def clean(self):
        cleaned_data = super().clean()
        destino_tipo = cleaned_data.get("destino_tipo")
        destinatario = cleaned_data.get("destinatario")

        if destino_tipo == Notificacao.USUARIO and not destinatario:
            self.add_error("destinatario", "Escolha o usuário que vai receber esta notificação.")

        if destino_tipo != Notificacao.USUARIO:
            cleaned_data["destinatario"] = None

        return cleaned_data
