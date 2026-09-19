from django.contrib import admin
from .models import Noticia, Pei

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data')
    list_filter = ('data',)
    search_fields = ('titulo', 'conteudo')

@admin.register(Pei)
class PeiAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data_envio', 'professor')
    list_filter = ('data_envio', 'professor')
    search_fields = ('titulo',)