"""Module die de urls afhandelt voor /handleidingen/"""

from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="handleidingen/overzicht.html"),
        name="handleiding_overzicht",
    ),
    path(
        "evenementen",
        TemplateView.as_view(
            template_name="handleidingen/evenementen/evenementen_lijst_handleiding.html"
        ),
        name="handleiding_evenementen",
    ),
    path(
        "evenementen/detail",
        TemplateView.as_view(
            template_name="handleidingen/evenementen/evenementen_detail_handleiding.html"
        ),
        name="handleiding_evenementen_detail",
    ),
    path(
        "deelnemers",
        TemplateView.as_view(
            template_name="handleidingen/deelnemers/deelnemers_lijst_handleiding.html"
        ),
        name="handleiding_deelnemers",
    ),
    path(
        "deelnemers/detail",
        TemplateView.as_view(
            template_name="handleidingen/deelnemers/deelnemers_detail_handleiding.html"
        ),
        name="handleiding_deelnemers_detail",
    ),
    path(
        "inschrijvingen",
        TemplateView.as_view(
            template_name="handleidingen/inschrijvingen/inschrijvingen_handleiding.html"
        ),
        name="handleiding_inschrijvingen",
    ),
]
