"""Deze module bevat de logica om lidgegevens op te vragen van de Groepsadministratie aan de hand van SOAP
"""

from dataclasses import dataclass, field
import os
from dotenv import load_dotenv

from zeep import Client
from zeep.transports import Transport

load_dotenv()

WSDL_URL = os.getenv("WSDL_URL")
APPLICATIE_NAAM = os.getenv("APPLICATIE_NAAM")

WEB_NAMESPACE = os.getenv("WEB_NAMESPACE")


@dataclass
class Functie:
    """Eén functie binnen een groep, bv. Groepsleiding of Webmaster."""
 
    code: str = ""
    beschrijving: str = ""
    groep: str = ""
    bdatum: str = ""
    edatum: str = ""
    gewicht: int = 0
    actief: bool = False
 
 
@dataclass
class Groep:
    """Eén groep waar het lid aan verbonden is, met de functies daarbinnen."""
 
    naam: str = ""
    groepsnummer: str = ""
    gewicht: int = 0
    actief: bool = False
    functies: list = field(default_factory=list)
 
 
@dataclass
class LidGegevens:
    """Alle lidgegevens uit een LidGegevensV3Response, in een handige vorm."""
 
    id: str = ""
    lidnummer: str = ""
    klantnummer: str = ""
    voornaam: str = ""
    naam: str = ""
    geboortedatum: str = ""
    emailadres: str = ""
    geslacht: str = ""
    gsmnummer: str = ""
    gebruikersnaam: str = ""
    groepen: list = field(default_factory=list)
 
    @property
    def volledige_naam(self):
        return f"{self.voornaam} {self.naam}".strip()
 
    @classmethod
    def van_respons(cls, resultaat):
        """
        Zet het antwoord van zeep (service.LidGegevensV3(...)) om naar een
        LidGegevens-object. zeep geeft de respons terug als een object met
        attributen die overeenkomen met de XML-elementen, bv.
        resultaat.groepen.groep is de lijst van <groep>-elementen.
 
        Data (bv. geboortedatum, bdatum) komt van zeep terug als
        datetime.date; die wordt hier omgezet naar een ISO-string
        (jjjj-mm-dd) zodat de template er zonder extra filters mee kan werken.
        """
        groepen = []
        groepen_container = getattr(resultaat, "groepen", None)
        ruwe_groepen = getattr(groepen_container, "groep", None) if groepen_container else None
 
        for ruwe_groep in ruwe_groepen or []:
            functies = []
            functies_container = getattr(ruwe_groep, "functies", None)
            ruwe_functies = getattr(functies_container, "functie", None) if functies_container else None
 
            for ruwe_functie in ruwe_functies or []:
                functies.append(
                    Functie(
                        code=getattr(ruwe_functie, "code", "") or "",
                        beschrijving=getattr(ruwe_functie, "beschrijving", "") or "",
                        groep=getattr(ruwe_functie, "groep", "") or "",
                        bdatum=_datum_naar_string(getattr(ruwe_functie, "bdatum", None)),
                        edatum=_datum_naar_string(getattr(ruwe_functie, "edatum", None)),
                        gewicht=getattr(ruwe_functie, "gewicht", 0) or 0,
                        actief=bool(getattr(ruwe_functie, "actief", False)),
                    )
                )
 
            groepen.append(
                Groep(
                    naam=getattr(ruwe_groep, "naam", "") or "",
                    groepsnummer=getattr(ruwe_groep, "groepsnummer", "") or "",
                    gewicht=getattr(ruwe_groep, "gewicht", 0) or 0,
                    actief=bool(getattr(ruwe_groep, "actief", False)),
                    functies=functies,
                )
            )
 
        return cls(
            id=getattr(resultaat, "id", "") or "",
            lidnummer=getattr(resultaat, "lidnummer", "") or "",
            klantnummer=getattr(resultaat, "klantnummer", "") or "",
            voornaam=getattr(resultaat, "voornaam", "") or "",
            naam=getattr(resultaat, "naam", "") or "",
            geboortedatum=_datum_naar_string(getattr(resultaat, "geboortedatum", None)),
            emailadres=getattr(resultaat, "emailadres", "") or "",
            geslacht=getattr(resultaat, "geslacht", "") or "",
            gsmnummer=getattr(resultaat, "gsmnummer", "") or "",
            gebruikersnaam=getattr(resultaat, "gebruikersnaam", "") or "",
            groepen=groepen,
        )
 
 
def _datum_naar_string(datumwaarde):
    """
    zeep geeft xsd:date-velden terug als datetime.date. Deze helper zet dat
    om naar een ISO-string (jjjj-mm-dd), en laat een lege waarde leeg.
    """
    if datumwaarde is None:
        return ""
    return datumwaarde.isoformat() if hasattr(datumwaarde, "isoformat") else str(datumwaarde)
 
 
def _maak_client(wsdl_url=WSDL_URL, transport=None):
    """Bouwt een zeep-client op basis van de WSDL."""
    return Client(wsdl=wsdl_url, transport=transport or Transport())
 
 
def haal_lidgegevens(gebruikersnaam, client=None, applicatie_naam=APPLICATIE_NAAM):
    """
    Vraagt de lidgegevens (LidGegevensV3) op voor het lid met het gegeven
    identificatie, en geeft die terug als een LidGegevens-object.
 
    Parameters
    ----------
    gebruikersnaam : str
        Het lidnummer of de gebruikersnaam (sgv:GebruikersnaamOfLidnummer)
        dat in het veld <gebruikersnaam> van de aanvraag komt.
    client : zeep.Client, optioneel
        Herbruikbare zeep-client. Wordt aangemaakt als er geen wordt meegegeven.
    applicatie_naam : str
        Waarde voor de SOAP-header <Applicatie>. Standaard "test-plain".
 
    Returns
    -------
    LidGegevens
        De lidgegevens uit de respons, met o.a. voornaam, naam, emailadres
        en de lijst van groepen/functies.
    """
    client = client or _maak_client()
 
    scope_type = client.get_type(f"{{{WEB_NAMESPACE}}}LidDataV3Keuze")
    scope = scope_type(
        basis={},
        functies={"actief": True},
    )
 
    resultaat = client.service.LidGegevensV3(
        gebruikersnaam=gebruikersnaam,
        scope=scope,
        _soapheaders={"applicatie": applicatie_naam},
    )
 
    return LidGegevens.van_respons(resultaat)

def haal_lidnaam(lid_id, client=None, applicatie_naam=APPLICATIE_NAAM):
    """
    Vraagt enkel voornaam + naam op voor het gegeven lid-id, als leesbare
    string ("Voornaam Naam"). Als de aanvraag om welke reden dan ook faalt
    (lid niet gevonden, service niet bereikbaar, ...) wordt het originele
    lid_id teruggegeven, zodat de aanroepende pagina niet crasht.
    """
    try:
        gegevens = haal_lidgegevens(lid_id, client=client, applicatie_naam=applicatie_naam)
        return gegevens.volledige_naam or str(lid_id)
    except Exception:
        return str(lid_id)