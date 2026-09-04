"""Package die alle data providers voor Weez geeft
"""

from .weez_provider import WeezClient

from .evenement_provider import (
    EvenementFilter,
    WeezEvenementProvider
)

from .inschrijving_provider import (
    InschrijvingFilter,
    WeezInschrijvingProvider
)

from .tarief_provider import (
    TariefFilter,
    WeezTariefProvider
)