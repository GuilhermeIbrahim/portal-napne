from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Noticia, Pei, FeedbackPublico, FeedbackPrivado


class NoticiaForm(forms.ModelForm):
    class Meta:
        model = Noticia
        fields = ["titulo", "imagem", "conteudo"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Título de notícia"}),
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

class PeiForm(forms.ModelForm):
    class Meta:
        model = Pei
        fields = ["titulo", "arquivo"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Título do PEI"}),
            "arquivo": forms.ClearableFileInput(attrs={"accept": ".pdf, .docx"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("titulo"),
            Field("arquivo"),
        )
        
class CadastroNapneForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150)
    email = forms.EmailField(label="E-mail")

    class Meta:
        model = get_user_model()
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("username"),
            Field("first_name"),
            Field("last_name"),
            Field("email"),
            Field("password1"),
            Field("password2"),
        )


class LoginNapneForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        widgets = {
            "conteudo": forms.Textarea(attrs={"placeholder": "Escreva seu comentário aqui...", "rows": 3}),
        }

class FeedbackPrivadoForm(forms.ModelForm):  
    noticia = forms.ModelChoiceField(queryset=Noticia.objects.all(), widget=forms.HiddenInput(), required=False)
    class Meta:
        model = FeedbackPrivado
        fields = ["noticia", "conteudo"]
        widgets = {
            "conteudo": forms.Textarea(attrs={"placeholder": "Escreva seu feedback aqui...", "rows": 3}),
        }