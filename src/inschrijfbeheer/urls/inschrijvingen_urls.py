"""Module die de urls afhandelt voor /inschrijvingen/
"""
from django.urls import path

from inschrijfbeheer import views

urlpatterns = [
    path("<str:inschrijving_id>", views.inschrijvingen_detail, name="inschrijving_detail"),
    path("<str:inschrijving_id>/vragen", views.inschrijvingen_vragen, name="inschrijving_vragen"),
]