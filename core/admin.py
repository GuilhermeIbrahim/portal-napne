from django.contrib import admin

from .models import Noticia, Pei, SolicitacaoNapne


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
