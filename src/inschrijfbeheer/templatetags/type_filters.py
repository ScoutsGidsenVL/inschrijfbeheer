from django import template

register = template.Library()

@register.filter
def is_boolean(waarde):
    return isinstance(waarde, bool)

@register.filter
def is_none(waarde):
    return waarde is None