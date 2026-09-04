# views.py
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from inschrijfbeheer.models import LogEntry, LogLevel
from inschrijfbeheer.utils.auth import check_rollen

TEKST_VELDEN = ["logger_name", "message", "module", "function", "user_identifier", "trace"]


@login_required
@check_rollen
def log_lijst(request: HttpRequest) -> HttpResponse:
    logs = LogEntry.objects.all()

    filters = {}
    for veld in TEKST_VELDEN:
        waarde = request.GET.get(veld, "").strip()
        if waarde:
            filters[veld] = waarde
            logs = logs.filter(**{f"{veld}__icontains": waarde})

    level_filter = request.GET.get("level", "").strip()
    if level_filter:
        logs = logs.filter(level=level_filter)

    van = request.GET.get("van", "").strip()
    if van:
        logs = logs.filter(created_at__date__gte=van)

    tot = request.GET.get("tot", "").strip()
    if tot:
        logs = logs.filter(created_at__date__lte=tot)

    paginator = Paginator(logs, 50)
    pagina = paginator.get_page(request.GET.get("pagina", 1))

    querystring = request.GET.copy()
    querystring.pop("pagina", None)

    return render(request, "logging/log_lijst.html", {
        "pagina": pagina,
        "levels": LogLevel.choices,
        "filters": {**filters, "level": level_filter, "van": van, "tot": tot},
        "basis_querystring": querystring.urlencode(),
    })