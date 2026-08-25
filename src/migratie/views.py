from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from .models import Evenement
from django.contrib.auth.decorators import login_required

KOLOMMEN = {
    "titel": "Titel",
    "beschrijving": "Beschrijving",
    "status": "Status",
    "locatie": "Locatie",
    "starttijd": "Starttijd",
    "eindtijd": "Eindtijd",
    "min_deelnemers": "Min. deelnemers",
    "max_deelnemers": "Max. deelnemers",
    "aantal_zelfde_groep": "Aantal uit dezelfde groep",
    "min_leeftijd": "Min. leeftijd",
    "categorie": "Categorie",
}

STANDAARD_KOLOMMEN = ["titel", "status", "locatie", "starttijd"]


# @login_required
def evenement_lijst(request: HttpRequest) -> HttpResponse:
    sleutelwoord: str = request.GET.get('q', '')
    gekozen_kolommen = [k for k in request.GET.getlist("kolom") if k in KOLOMMEN]
    if not gekozen_kolommen:
        gekozen_kolommen = STANDAARD_KOLOMMEN

    evenementen = Evenement.objects.select_related("status", "locatie", "categorie").filter(titel__contains=sleutelwoord.strip())

    rijen = [
        (evenement.id, [getattr(evenement, kolom) for kolom in gekozen_kolommen])
        for evenement in evenementen
    ]

    return render(request, "evenementen/evenementen_lijst.html", {
        "alle_kolommen": KOLOMMEN,
        "gekozen_kolommen": gekozen_kolommen,
        "gekozen_labels": [KOLOMMEN[k] for k in gekozen_kolommen],
        "rijen": rijen,
    })

# @login_required
def evenement_detail(request: HttpRequest, id: str) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=id)

    return render(request, "evenementen/evenementen_detail.html", {
        "evenement": evenement
    })

def evenement_inschrijvingen(request: HttpRequest, id:str) -> HttpResponse:
    return render(request, "evenementen/evenementen_inschrijvingen.html", {
        "value": "oeps"
    })