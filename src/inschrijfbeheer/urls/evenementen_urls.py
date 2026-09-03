"""Module die de urls afhandelt voor /evenementen/
"""
from django.urls import path

from inschrijfbeheer import views

urlpatterns = [
    path("", views.evenement_lijst, name="evenement_lijst"),
    path("<str:id>/", views.evenement_detail, name="evenement_detail"),
    path("<str:id>/inschrijvingen/", views.evenement_inschrijvingen, name="evenement_inschrijvingen"),
    path("<str:evenement_id>/inschrijvingen/attesten/download", views.evenementen_inschrijvingen_attesten_download, name="evenementen_inschrijvingen_attesten_download"),
    path("<str:evenement_id>/inschrijvingen/attesten/mail", views.evenementen_inschrijvingen_attesten_mail, name="evenementen_inschrijvingen_attesten_mail"),
    path("<str:id>/vragen/", views.evenement_vragen, name="evenement_vragen"),
    path("<str:evenement_id>/vragen/<str:vraag_id>/antwoorden/", views.evenement_vraag_antwoorden, name="evenement_vraag_antwoorden"),
]