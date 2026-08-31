"""Module die een klasse bevat die als interface kan dienen voor synchronisatie met een databron
"""
from dataclasses import dataclass
import logging

ObjectCreatie = tuple[int, int, int]

@dataclass
class SynchronisatieInfo:
    """Klasse die de resultaten van een synchronisatie bijhoudt.
    
    Attributes:
        succes (bool): geeft aan of de synchronisatie tot het einde kon lopen
        resultaten (dict[type, ObjectCreatie]): geeft voor elke model aan hoeveel objecten aangemaakt, bijgewerkt of overgeslagen werden
    """
    succes: bool
    resultaten: dict[type, ObjectCreatie]

    def formatteer(self):
        weergave = f"Synchronisatie {"succesvol" if self.succes else "gefaald"}:\n"
        for model, resultaat in self.resultaten.items():
            weergave += f"{model} model maakte {resultaat[0]} nieuwe objecten aan, werkte {resultaat[1]} objecten bij en sloeg {resultaat[2]} objecten over\n"
        return weergave

class Mapper:
    """Superklasse voor mappers om een gelijkaardige interface te geven
    """

    logger = logging.getLogger("inschrijfbeheer")

    def synchroniseer(self) -> SynchronisatieInfo:
        raise NotImplementedError("Deze methode dient geïmplemnteerd door een subklasse")

    def log_info(self) -> None:
        pass