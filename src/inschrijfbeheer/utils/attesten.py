from io import BytesIO
import zipfile

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from inschrijfbeheer.models import Inschrijving, Deelnemer


def genereer_deelname_attest(inschrijving_id: str):

    inschrijving = Inschrijving.objects.select_related("evenement", "lid").get(id=inschrijving_id)

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.drawString(100, 750, str(inschrijving.lid))
    pdf.drawString(100, 800, str(inschrijving.evenement))
    pdf.save()

    buffer.seek(0)
    return buffer

def genereer_zip_attesten(inschrijvingen: list[Inschrijving]) -> BytesIO:
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w") as zip_bestand:
        for inschrijving in inschrijvingen:
            attest = genereer_deelname_attest(inschrijving.id)
            zip_bestand.writestr(f"deelname_attest_{inschrijving.lid}.pdf", attest.getvalue())

    buffer.seek(0)
    return buffer