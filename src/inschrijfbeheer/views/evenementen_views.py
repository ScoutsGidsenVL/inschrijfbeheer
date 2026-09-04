from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from inschrijfbeheer.models import Evenement, Inschrijving, EvenementVraag, InschrijvingVraagAntwoord, Categorie
from inschrijfbeheer.utils.synchronisatie import synchroniseer_evenement
from inschrijfbeheer.utils.attesten import genereer_zip_attesten, genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mails

KOLOMMEN = {
    "id": "ID",
    "is_weez": "Weezevent",
    "titel": "Titel",
    "categorie": "Categorie",
    "status": "Status",
}

@login_required
def evenement_lijst(request: HttpRequest) -> HttpResponse:
    zoekterm: str = request.GET.get('q', '').strip()
    categorie_naam: str = request.GET.get('categorie', '').strip()
    weez_filter: str = request.GET.get("weez", '')
    sorteer: str = request.GET.get("sorteer", '').strip()

    evenementen = Evenement.objects.select_related("status", "categorie").filter(
        Q(titel__icontains=zoekterm)
        | Q(id__icontains=zoekterm)
    )

    if categorie_naam:
        categorie = Categorie.objects.get(naam=categorie_naam)
        evenementen = evenementen.filter(
            categorie=categorie.id
        )

    if weez_filter:
        if weez_filter == '1':
            evenementen = evenementen.filter(is_weez=True)
        else:
            evenementen = evenementen.exclude(is_weez=True)

    if sorteer.lstrip("-") in KOLOMMEN:
        evenementen = evenementen.order_by(sorteer)

    categorieen = Categorie.objects.all()

    return render(request, "evenementen/evenementen_lijst.html", {
        "evenementen": evenementen,
        "categorieen": categorieen,
    })

@login_required
def evenement_detail(request: HttpRequest, id: str) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=id)
    synchroniseer = request.GET.get("sync", None)
    if synchroniseer is not None and synchroniseer == '1':
        synchroniseer_evenement(evenement=evenement)
        return redirect('evenement_detail', id=id)


    return render(request, "evenementen/evenementen_detail.html", {
        "evenement": evenement
    })

@login_required
def evenement_inschrijvingen(request: HttpRequest, id:str) -> HttpResponse:
    evenement = get_object_or_404(Evenement, id=id)
    zoekterm = request.GET.get('q', '')
 
    kolommen = ["ID", "Lid", "Deelnemertype", "Tijdstip", "Betaald", "Annulatie", "Aanwezig"]

    queryset = Inschrijving.objects.filter(evenement=id).select_related("deelnemertype", "evenement", "lid")
    if zoekterm:
        queryset = queryset.filter(
            Q(lid__id__icontains=zoekterm)
            | Q(lid__voornaam__icontains=zoekterm)
            | Q(lid__achternaam__icontains=zoekterm)
            | Q(lid__mailadres__icontains=zoekterm)
        )

    aanwezig_filter = request.GET.get("aanwezig", "")
    if aanwezig_filter == "1":
        queryset = queryset.filter(annulatie__isnull=True)
    elif aanwezig_filter == "0":
        queryset = queryset.exclude(annulatie__isnull=True)

    inschrijvingen = []
    for instantie in queryset:

        annulatie = ""
        aanwezig = True
        if instantie.annulatie:
            annulatie = instantie.annulatie
            aanwezig = False
        elif instantie.lid.foutboodschap:
            annulatie = instantie.lid.foutboodschap
            aanwezig = False

        inschrijvingen.append({
            "instantie": instantie,
            "waarden": [
                instantie.id,
                instantie.lid,
                str(instantie.deelnemertype),
                instantie.tijdstip,
                instantie.prijs,
                annulatie,
                aanwezig,
            ],
        })
 
    return render(request, "evenementen/evenementen_inschrijvingen.html", {
        "kolommen": kolommen,
        "inschrijvingen": inschrijvingen,
        "evenement": evenement,
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


@login_required
def evenementen_inschrijvingen_attesten_download(request: HttpRequest, evenement_id: str) -> HttpResponse:
    inschrijvingen = Inschrijving.objects.select_related("lid").filter(evenement=evenement_id, annulatie__isnull=True, lid__foutboodschap__isnull=True)
    buffer = genereer_zip_attesten(inschrijvingen)

    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="deelname_attesten.zip"'
    return response

@login_required
def evenementen_inschrijvingen_attesten_mail(request: HttpRequest, evenement_id: str) -> HttpResponse:
    inschrijvingen = Inschrijving.objects.select_related("lid").filter(evenement=evenement_id, annulatie__isnull=True, lid__foutboodschap__isnull=True)

    maildata = []
    for inschrijving in inschrijvingen:
        maildata.append((genereer_deelname_attest(inschrijving.id), inschrijving.lid))

    stuur_attest_mails(maildata)
    return redirect("evenement_inschrijvingen", id=evenement_id)