from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required

from migratie.models import Inschrijving

from migratie.utils.soap import haal_lidgegevens

def deelnemers_lijst(request: HttpRequest) -> HttpResponse:
    zoekterm = request.GET.get("q", '')
    deelnemers = Inschrijving.objects.values("lid").filter(lid__icontains=zoekterm).distinct() # Eventueel aanpassen naar apart model

    deelnemers = [haal_lidgegevens(lid_id["lid"]) for lid_id in deelnemers]

    return render(request, "deelnemers/deelnemers_lijst.html", {
        "deelnemers": deelnemers
    })

def deelnemers_detail(request: HttpRequest, id: str) -> HttpResponse:
    deelnemer = haal_lidgegevens(id)

    return render(request, "deelnemers/deelnemers_detail.html", {
        "deelnemer": deelnemer
    })