from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from migratie.models import Evenement, Inschrijving, EvenementVraag, InschrijvingVraagAntwoord
from django.contrib.auth.decorators import login_required
from migratie.utils.soap import haal_lidnaam

KOLOMMEN = {
    "id": "ID",
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

STANDAARD_KOLOMMEN = ["id", "titel", "status", "locatie", "starttijd"]


@login_required
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

@login_required
def evenement_detail(request: HttpRequest, id: str) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=id)

    return render(request, "evenementen/evenementen_detail.html", {
        "evenement": evenement
    })

@login_required
def evenement_inschrijvingen(request: HttpRequest, id:str) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=id)
 
    kolommen = ["ID", "Lid", "Deelnemertype", "Tijdstip", "Betaald", "Annulatie", "Aanwezig"]
    namen_per_lid_id = {}

    aanwezig_filter = request.GET.get("aanwezig", "")

    queryset = Inschrijving.objects.filter(evenement=id).select_related("deelnemertype", "evenement")
    if aanwezig_filter == "1":
        queryset = queryset.filter(annulatie__isnull=True)
    elif aanwezig_filter == "0":
        queryset = queryset.exclude(annulatie__isnull=True)

    inschrijvingen = []
    for instantie in queryset:
        lid_id = instantie.lid
 
        if lid_id not in namen_per_lid_id:
            namen_per_lid_id[lid_id] = haal_lidnaam(lid_id)
 
        inschrijvingen.append({
            "instantie": instantie,
            "waarden": [
                instantie.id,
                namen_per_lid_id[lid_id],
                str(instantie.deelnemertype),
                instantie.tijdstip,
                instantie.prijs,
                instantie.annulatie,
                instantie.annulatie is None,
            ],
        })
 
    return render(request, "evenementen/evenementen_inschrijvingen.html", {
        "kolommen": kolommen,
        "inschrijvingen": inschrijvingen,
        "evenement": evenement,
        "aanwezig_filter": aanwezig_filter,
    })

@login_required
def evenement_inschrijving_detail(request: HttpRequest, evenement_id: str, inschrijving_id: str) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=evenement_id)
    inschrijving = get_object_or_404(Inschrijving, id=inschrijving_id)


    vraag_antwoorden = InschrijvingVraagAntwoord.objects.filter(inschrijving=inschrijving_id).select_related("vraag", "vraag__type").order_by("vraag__volgorde")
    return render(request, "evenementen/inschrijvingen/inschrijvingen_detail.html", {
        "vraag_antwoorden" : vraag_antwoorden,
        "evenement": evenement,
        "inschrijving": inschrijving,
    })

@login_required
def evenement_vragen(request: HttpRequest, id: str) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=id)

    vragen = EvenementVraag.objects.filter(evenement=id).select_related("type").order_by("volgorde")
    return render(request, "evenementen/vragen/evenementen_vragen.html", {
        "vragen" : vragen,
        "evenement": evenement
    })

@login_required
def evenement_vraag_antwoorden(request: HttpRequest, evenement_id: str, vraag_id) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=evenement_id)
    vraag = get_object_or_404(EvenementVraag, id=vraag_id)

    antwoorden = InschrijvingVraagAntwoord.objects.filter(vraag=vraag_id)
    return render(request, "evenementen/vragen/evenementen_vragen_antwoorden.html", {
        "antwoorden" : antwoorden,
        "vraag": vraag,
        "evenement": evenement
    })