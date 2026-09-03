"""Module met extra functies/decorators voor de authenticatie/autorisatie van Inschrijfbeheer
"""
from functools import wraps
from django.http import Http404
from .soap import haal_lidgegevens, LidGegevens

def check_rollen(rol="personeel"):
    """Functie die een decorator teruggeeft voor een bepaalde rol die gecheckt moet worden

    Args:
        rol (str, optional): de rol die de persoon moet hebben binnen X1207G. Defaults to "personeel".
    """
    def check_rollen_decorator(func):

        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                profiel: LidGegevens = haal_lidgegevens(request.user)

                for groep in profiel.groepen:
                    if groep.naam =="X1207G":
                        for functie in groep.functies:
                            if functie.code == rol:
                                return func(request, *args, **kwargs)
            except:
                raise Http404()
            raise Http404()

        return wrapper

    return check_rollen_decorator