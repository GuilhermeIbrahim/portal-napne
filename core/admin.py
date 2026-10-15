from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    FeedbackPrivado,
    FeedbackPublico,
    HistoricoPei,
    Noticia,
    Notificacao,
    Pei,
    SolicitacaoNapne,
    Usuario,
    VersaoPei,
)

admin.site.register(Usuario, UserAdmin)

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data')
    list_filter = ('data',)
    search_fields = ('titulo', 'conteudo')

class VersaoPeiInline(admin.TabularInline):
    model = VersaoPei
    extra = 0
    can_delete = False
    fields = ('numero', 'arquivo', 'enviado_por', 'enviado_em', 'comentario')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class HistoricoPeiInline(admin.TabularInline):
    model = HistoricoPei
    extra = 0
    can_delete = False
    fields = ('alterado_em', 'status_anterior', 'status_novo', 'alterado_por', 'versao', 'observacao')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pei)
class PeiAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'status', 'data_envio', 'professor')
    list_filter = ('status', 'data_envio', 'professor')
    search_fields = ('titulo',)
    inlines = [VersaoPeiInline, HistoricoPeiInline]

    def get_readonly_fields(self, request, obj=None):
        # Status e arquivo só mudam pelo fluxo de análise/nova versão; assim o histórico não fica incoerente.
        if obj:
            return ('status', 'arquivo')
        return ()


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

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'destino_tipo', 'destinatario', 'remetente', 'criado_em')
    list_filter = ('destino_tipo', 'criado_em')
    search_fields = ('titulo', 'conteudo')


@admin.register(HistoricoPei)
class HistoricoPeiAdmin(admin.ModelAdmin):
    list_display = ('pei', 'status_anterior', 'status_novo', 'alterado_por', 'alterado_em')
    list_filter = ('status_novo',)
