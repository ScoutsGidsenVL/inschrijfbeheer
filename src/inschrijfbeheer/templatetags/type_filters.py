from django import template

register = template.Library()

@register.filter
def is_boolean(waarde):
    return isinstance(waarde, bool)

@register.filter
def is_none(waarde):
    return waarde is None

@register.simple_tag(takes_context=True)
def sorteer_url(context, kolom):
    """Geeft de querystring terug voor een link die op `kolom` sorteert,
    of de sortering omdraait als er al op `kolom` gesorteerd wordt."""
    request = context["request"]
    huidig = request.GET.get("sorteer", "")

    nieuw = f"-{kolom}" if huidig == kolom else kolom

    params = request.GET.copy()
    params["sorteer"] = nieuw
    return "?" + params.urlencode()


@register.simple_tag(takes_context=True)
def sorteer_icoon(context, kolom):
    """Toont een pijltje als er op `kolom` gesorteerd wordt."""
    huidig = context["request"].GET.get("sorteer", "")
    if huidig == kolom:
        return "↑"
    elif huidig == f"-{kolom}":
        return "↓"
    return "⇵"