from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    FeedbackPrivado,
    FeedbackPublico,
    HistoricoPei,
    Noticia,
    Notificacao,
    Pei,
    RegistroAcessoPei,
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
    fields = ('numero', 'arquivo_privado', 'enviado_por', 'enviado_em', 'comentario')
    readonly_fields = fields

    @admin.display(description='Arquivo')
    def arquivo_privado(self, versao):
        return f'{versao.nome_do_download()} (área privada)' if versao.pk else '-'

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
    list_display = ('titulo', 'estudante_nome', 'periodo_letivo', 'status', 'data_envio', 'professor')
    list_filter = ('status', 'periodo_letivo', 'data_envio', 'professor')
    search_fields = ('titulo',)
    inlines = [VersaoPeiInline, HistoricoPeiInline]
    exclude = ('arquivo',)  
    readonly_fields = ('status',)

    def has_add_permission(self, request):
        return False

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

@admin.register(RegistroAcessoPei)
class RegistroAcessoPeiAdmin(admin.ModelAdmin):
    """Trilha de auditoria: só leitura. Ninguém altera nem apaga registros pelo admin."""

    list_display = ('criado_em', 'pei_id', 'acao', 'versao_numero', 'usuario')
    list_filter = ('acao', 'criado_em')
    date_hierarchy = 'criado_em'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
