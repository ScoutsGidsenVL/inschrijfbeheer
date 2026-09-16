"""Package die alle data providers voor Weez geeft
"""

from .weez_client import WeezClient

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

from .form_provider import (
    FormFilter,
    WeezFormProvider,
)