import logging
import os
from dotenv import load_dotenv
from io import BytesIO

from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string

from inschrijfbeheer.models import Deelnemer

logger = logging.getLogger("inschrijfbeheer")

load_dotenv()
FROM_MAIL_ADDRESS = os.getenv("FROM_MAIL_ADDRESS")

def stuur_attest_mail(attest, deelnemer: Deelnemer, connection=None):
    html_content = render_to_string(
        "mails/attesten_mail.html",
        context={
            "deelnemer": deelnemer
        },
    )

    msg = EmailMessage(
        subject="Attest voor jouw deelname",
        from_email=FROM_MAIL_ADDRESS,
        body=html_content,
        to=[deelnemer.mailadres],
        connection=connection,
    )
    msg.attach("deelname_attest.pdf", attest.getvalue(), "application/pdf")
    msg.content_subtype = "html"
    msg.send()
    logger.info(f"Mail verstuurd naar {deelnemer.mailadres}")


def stuur_attest_mails(attesten_en_deelnemers: list[tuple[BytesIO, Deelnemer]]):
    connection = get_connection()
    connection.open()

    try:
        for attest, deelnemer in attesten_en_deelnemers:
            stuur_attest_mail(attest, deelnemer, connection=connection)
    finally:
        connection.close()