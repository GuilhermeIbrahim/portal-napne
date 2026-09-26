from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Noticia, Pei, SolicitacaoNapne, Usuario, FeedbackPublico, FeedbackPrivado

admin.site.register(Usuario, UserAdmin)

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

@admin.register(SolicitacaoNapne)
class SolicitacaoNapneAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'criado_em', 'avaliado_por')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

@admin.register(FeedbackPublico)
class FeedbackPublicoAdmin(admin.ModelAdmin):
    list_display = ('noticia', 'autor', 'data')
    list_filter = ('data',)
    search_fields = ('noticia__titulo', 'autor__username', 'autor__first_name', 'autor__last_name')
    
@admin.register(FeedbackPrivado)
class FeedbackPrivadoAdmin(admin.ModelAdmin):
    list_display = ('noticia', 'autor', 'data')
    list_filter = ('data',)
    search_fields = ('noticia__titulo', 'autor__username', 'autor__first_name', 'autor__last_name')
