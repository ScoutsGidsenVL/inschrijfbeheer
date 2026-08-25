from django.shortcuts import render
from django.template.loader import render_to_string
from .models import Evenement
from django.contrib.auth.decorators import login_required

@login_required
def evenement_lijst(request):
    evenementen = Evenement.objects.all()
    return render(
        request,
        "evenementen/evenement_lijst.html",
        {"evenementen": evenementen}
    )