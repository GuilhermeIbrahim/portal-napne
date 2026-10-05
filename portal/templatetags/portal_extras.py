from django import template

register = template.Library()

@register.filter
def has_group(user, group_name):
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()

@register.filter
def resto(valor, divisor):
    try:
        return int(valor) % int(divisor)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0