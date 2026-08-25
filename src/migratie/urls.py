from django.urls import path

from . import views

urlpatterns = [
    path("evenementen", views.evenement_lijst, name="evenement_lijst"),
    path("evenement/<str:id>", views.evenement_detail, name="evenement_detail")
]