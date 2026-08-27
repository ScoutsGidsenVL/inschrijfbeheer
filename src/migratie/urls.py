from django.urls import path

from . import views

urlpatterns = [
    path("evenementen/", views.evenement_lijst, name="evenement_lijst"),
    path("evenementen/<str:id>/", views.evenement_detail, name="evenement_detail"),
    path("evenementen/<str:id>/inschrijvingen/", views.evenement_inschrijvingen, name="evenement_inschrijvingen"),
    path("deelnemers/", views.deelnemers_lijst, name="deelnemers_lijst"),
    path("deelnemers/<str:id>/", views.deelnemers_detail, name="deelnemers_detail")
]