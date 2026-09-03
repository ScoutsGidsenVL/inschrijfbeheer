from io import BytesIO
import zipfile
from pypdf import PdfReader, PdfWriter
from dotenv import load_dotenv
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from inschrijfbeheer.models import Inschrijving
from inschrijfbeheer.utils.soap import haal_lidgegevens

load_dotenv()
PDF_PAD = os.getenv("DEELNAME_ATTEST_PDF")


def genereer_deelname_attest(inschrijving_id: str):
    inschrijving = Inschrijving.objects.select_related("evenement", "lid").get(id=inschrijving_id)
    lidgegevens = haal_lidgegevens(inschrijving.lid.id)

    achtergrond = PdfReader(PDF_PAD)
    pagina_achtergrond = achtergrond.pages[0]

    breedte = float(pagina_achtergrond.mediabox.width)
    hoogte = float(pagina_achtergrond.mediabox.height)

    overlay_buffer = BytesIO()
    pdf = canvas.Canvas(overlay_buffer, pagesize=(breedte, hoogte))

    pdf.drawString(300, 545, f"{inschrijving.evenement.starttijd.strftime("%d/%m/%Y")} - {inschrijving.evenement.eindtijd.strftime("%d/%m/%Y")}")
    pdf.drawString(300, 525, inschrijving.evenement.locatie_naam)
    pdf.drawString(300, 505, f"€ {'{:.2g}'.format(inschrijving.prijs)}")
    pdf.drawString(300, 455, str(lidgegevens.lidnummer))
    pdf.drawString(300, 435, lidgegevens.volledige_naam)
    pdf.drawString(300, 415, "ADRES")
    pdf.drawString(300, 360, lidgegevens.volledige_naam)
    pdf.drawString(300, 340, lidgegevens.rekeningnummer)

    pdf.save()
    overlay_buffer.seek(0)

    overlay = PdfReader(overlay_buffer)
    pagina_achtergrond.merge_page(overlay.pages[0])

    writer = PdfWriter()
    writer.add_page(pagina_achtergrond)

    resultaat_buffer = BytesIO()
    writer.write(resultaat_buffer)
    resultaat_buffer.seek(0)
    return resultaat_buffer

def genereer_zip_attesten(inschrijvingen: list[Inschrijving]) -> BytesIO:
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w") as zip_bestand:
        for inschrijving in inschrijvingen:
            attest = genereer_deelname_attest(inschrijving.id)
            zip_bestand.writestr(f"deelname_attest_{inschrijving.lid}.pdf", attest.getvalue())

    buffer.seek(0)
    return buffer