"""
URL configuration for inschrijfbeheer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""

from django.conf import settings
from django.urls import include, path
from django.views.generic.base import RedirectView
from django.views.static import serve

from inschrijfbeheer.utils.auth import check_rollen
from inschrijfbeheer.views import log_lijst
from inschrijfbeheer.views.auth_views import frontchannel_logout, geen_toegang

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="evenement_lijst"), name="home"),
    # vóór de include, zodat deze URL niet door mozilla_django_oidc afgehandeld wordt
    path("oidc/frontchannel-logout/", frontchannel_logout, name="oidc_frontchannel_logout"),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("geen-toegang/", geen_toegang, name="geen_toegang"),
    path(
        "docs/",
        check_rollen(serve),
        {"document_root": settings.BASE_DIR / ".." / "docs", "path": "README.md"},
    ),  # README te vinden via docs/
    path(
        "docs/<path:path>",
        check_rollen(serve),
        {"document_root": settings.BASE_DIR / ".." / "docs"},
    ),  # technische documentatie terug te vinden via /docs/<naam>
    path("logs/", log_lijst, name="log_lijst"),
    path("evenementen/", include("inschrijfbeheer.urls.evenementen_urls")),
    path("deelnemers/", include("inschrijfbeheer.urls.deelnemers_urls")),
    path("inschrijvingen/", include("inschrijfbeheer.urls.inschrijvingen_urls")),
    path("handleidingen/", include("inschrijfbeheer.urls.handleidingen_urls")),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
