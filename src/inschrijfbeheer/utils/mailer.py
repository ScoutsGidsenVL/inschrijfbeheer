import logging
import os
from dotenv import load_dotenv

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from inschrijfbeheer.models import Deelnemer

logger = logging.getLogger("inschrijfbeheer")

load_dotenv()
FROM_MAIL_ADDRESS = os.getenv("FROM_MAIL_ADDRESS")

def stuur_attest_mail(attest, deelnemer: Deelnemer):
    html_content = render_to_string(
        "mails/attesten_mail.html",
        context={
            "deelnemer": deelnemer
        },
    )

    msg = EmailMessage(
        subject=f"Attest voor jouw deelname",
        from_email=FROM_MAIL_ADDRESS,
        body=html_content,
        to=[deelnemer.mailadres],
    )
    msg.attach("Deelname attest", attest.getvalue(), "application/pdf")
    msg.content_subtype = "html"
    msg.send()
    logger.info(f"Mail verstuurd naar {deelnemer.mailadres}")
