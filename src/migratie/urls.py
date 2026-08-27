from django.urls import path

from . import views

urlpatterns = [
    path("evenementen/", views.evenement_lijst, name="evenement_lijst"),
    path("evenementen/<str:id>/", views.evenement_detail, name="evenement_detail"),
    path("evenementen/<str:id>/inschrijvingen/", views.evenement_inschrijvingen, name="evenement_inschrijvingen"),
    path("evenementen/<str:evenement_id>/inschrijvingen/<str:inschrijving_id>", views.evenement_inschrijving_detail, name="evenement_inschrijving_detail"),
    path("evenementen/<str:id>/vragen/", views.evenement_vragen, name="evenement_vragen"),
    path("evenementen/<str:evenement_id>/vragen/<str:vraag_id>/antwoorden/", views.evenement_vraag_antwoorden, name="evenement_vraag_antwoorden"),
    path("deelnemers/", views.deelnemers_lijst, name="deelnemers_lijst"),
    path("deelnemers/<str:id>/", views.deelnemers_detail, name="deelnemers_detail")
]