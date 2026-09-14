from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Div

from .models import Noticia

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