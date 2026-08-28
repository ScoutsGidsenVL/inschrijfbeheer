"""Module die de urls afhandelt voor /deelnemers/
"""
from django.urls import path

from inschrijfbeheer import views

urlpatterns = [
    path("", views.deelnemers_lijst, name="deelnemers_lijst"),
    path("<str:id>/", views.deelnemers_detail, name="deelnemers_detail"),
    path("<str:id>/inschrijvingen", views.deelnemers_inschrijvingen, name="deelnemers_inschrijvingen"),
]