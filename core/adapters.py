import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)

SUAP_TIPO_USUARIO_PARA_GRUPO = {
    "Aluno": "Estudante",
    "Servidor": "Servidor",
}

GRUPOS_GERENCIADOS = set(SUAP_TIPO_USUARIO_PARA_GRUPO.values())

class SuapSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        extra_data = sociallogin.account.extra_data
        tipo_usuario = extra_data.get("tipo_usuario")
        
        logger.info(
            "Login via SUAP: identificacao=%s tipo_usuario=%r",
            extra_data.get("identificacao"), tipo_usuario,
        )
        
        user = sociallogin.user
        if not user or not user.pk:
            return
        self._sincronizar_grupo(user, tipo_usuario)
        
    def populate_user(self, request, sociallogin, data):
        return super().populate_user(request, sociallogin, data)
        
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        tipo_usuario = sociallogin.account.extra_data.get("tipo_usuario")
        self._sincronizar_grupo(user, tipo_usuario)
        return user
        
    def _sincronizar_grupo(self, user, tipo_usuario):
        nome_grupo = SUAP_TIPO_USUARIO_PARA_GRUPO.get(tipo_usuario)
        if nome_grupo is None:
            logger.warning(
                "tipo_usuario do SUAP sem mapeamento conhecido: %r (usuário=%s).",
                tipo_usuario, user.get_username(),
            )
            return
        grupo, _ = Group.objects.get_or_create(name=nome_grupo)
        outros_grupos = GRUPOS_GERENCIADOS - {nome_grupo}
        if outros_grupos:
            user.groups.remove(*Group.objects.filter(name__in=outros_grupos))
        user.groups.add(grupo)
            