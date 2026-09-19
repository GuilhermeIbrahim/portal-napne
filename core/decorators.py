from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def napne_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name="NAPNE").exists():
            raise PermissionDenied("Esta ação é restrita a servidores do NAPNE.")
        return view_func(request, *args, **kwargs)
    return wrapper

def professor_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name="Servidor").exists():
            raise PermissionDenied("Esta ação é restrita a professores.")
        return view_func(request, *args, **kwargs)
    return wrapper