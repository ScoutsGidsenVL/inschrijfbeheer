from django.urls import path

from . import views

urlpatterns = [
    path("evenementen/", views.evenement_lijst, name="evenement_lijst"),
    path("evenementen/<str:id>/", views.evenement_detail, name="evenement_detail")
]