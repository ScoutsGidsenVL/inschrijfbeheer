from dataclasses import dataclass
from . import WeezClient

@dataclass(frozen=True)
class FormFilter:
    evenement_id: str
    deelnemer_id: str


class WeezFormProvider:
    """Het form-veld van één deelnemer, met de sleutels die Weez zelf gebruikt.

    De oude API geeft de vragen met hun label maar zonder sleutel, de v3-API
    geeft ze met hun sleutel maar zonder label. Deze provider levert dat
    tweede stuk, zodat de twee gekoppeld kunnen worden.
    """

    def __init__(self, client: WeezClient):
        self.client = client

    def haal_op(self, filter: FormFilter) -> dict:
        """Geeft de sleutel-waardeparen van het formulier van één deelnemer.

        Args:
            filter (FormFilter): evenement en deelnemer

        Returns:
            dict: sleutel naar antwoord, met een alias bij een standaardvraag
                en een Weez-vraag-id bij een eigen vraag
        """
        respons = self.client.get(
            f"v3/evenement/{filter.evenement_id}/participants/{filter.deelnemer_id}",
            parameters={"loadFormAnswers": "1"},
        )
        return respons.get("form") or {}