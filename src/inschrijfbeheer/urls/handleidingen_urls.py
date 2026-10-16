"""Module die de urls afhandelt voor /handleidingen/"""

from django.urls import path
from django.views.generic import TemplateView

from inschrijfbeheer.utils.auth import check_rollen

urlpatterns = [
    path(
        "",
        check_rollen(TemplateView.as_view(template_name="handleidingen/overzicht.html")),
        name="handleiding_overzicht",
    ),
    path(
        "evenementen",
        check_rollen(TemplateView.as_view(
            template_name="handleidingen/evenementen/evenementen_lijst_handleiding.html"
        )),
        name="handleiding_evenementen",
    ),
    path(
        "evenementen/detail",
        check_rollen(TemplateView.as_view(
            template_name="handleidingen/evenementen/evenementen_detail_handleiding.html"
        )),
        name="handleiding_evenementen_detail",
    ),
    path(
        "deelnemers",
        check_rollen(TemplateView.as_view(
            template_name="handleidingen/deelnemers/deelnemers_lijst_handleiding.html"
        )),
        name="handleiding_deelnemers",
    ),
    path(
        "deelnemers/detail",
        check_rollen(TemplateView.as_view(
            template_name="handleidingen/deelnemers/deelnemers_detail_handleiding.html"
        )),
        name="handleiding_deelnemers_detail",
    ),
    path(
        "inschrijvingen",
        check_rollen(TemplateView.as_view(
            template_name="handleidingen/inschrijvingen/inschrijvingen_handleiding.html"
        )),
        name="handleiding_inschrijvingen",
    ),
]
