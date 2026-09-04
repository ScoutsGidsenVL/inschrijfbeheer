"""
URL configuration for inschrijfbeheer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings

from inschrijfbeheer.views import log_lijst

urlpatterns = [
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("", login_required(TemplateView.as_view(template_name="home.html")), name="home"),
    path("docs/", serve, {"document_root": settings.BASE_DIR / '..' / 'docs', "path": "README.md"}), # README te vinden via docs/
    path("docs/<path:path>", serve, {"document_root": settings.BASE_DIR / '..' / 'docs'}), # technische documentatie terug te vinden via /docs/<naam>
    path("logs/", log_lijst, name="log_lijst"),
    path("evenementen/", include("inschrijfbeheer.urls.evenementen_urls")),
    path("deelnemers/", include("inschrijfbeheer.urls.deelnemers_urls")),
    path("inschrijvingen/", include("inschrijfbeheer.urls.inschrijvingen_urls")),
]
