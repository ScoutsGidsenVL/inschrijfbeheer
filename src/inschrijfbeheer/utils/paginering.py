from django.core.paginator import Page, Paginator
from django.http import HttpRequest


def pagineer(request: HttpRequest, queryset, per_pagina: int = 5) -> tuple[Page, str]:
    """Pagineert een queryset op basis van de 'page' GET-parameter.

    Args:
        request (HttpRequest): HTTP request, gebruikt om de huidige pagina
            en de overige GET-parameters op te halen.
        queryset: De te pagineren queryset.
        per_pagina (int): Aantal elementen per pagina.

    Returns:
        tuple[Page, str]: De opgevraagde pagina en een querystring met alle
        GET-parameters behalve 'page', klaar voor gebruik in paginalinks.
    """
    paginator = Paginator(queryset, per_pagina)
    pagina = paginator.get_page(request.GET.get("page"))

    overige_parameters = request.GET.copy()
    overige_parameters.pop("page", None)

    return pagina, overige_parameters.urlencode()