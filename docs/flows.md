# Flows

Omdat bepaalde functionaliteiten aanpassingen maken in de Weez API wordt in dit bestand omschreven hoe datastromen die niet enkel lezen uit de Integreat databank of van de Weez API.

## Vragen inschrijving aanpassen

> [!WARNING]
> Dit is de enige flow die niet te doen valt zonder de oude API en daarom dus ook gebruik maakt van een oude endpoint

Het is mogelijk om via `/inschrijvingen/<id>/vragen` de vragen van een deelnemer aan te passen.
 1. Bij het opslaan van deze vragen worden de vragen van de deelnemer geüpdatet via de Weez API.
 2. Vervolgens wordt een synchronisatie van de deelnemers van het evenement waarvoor de inschrijving geldde opgeroepen via een taak.
 3. Deze taak synchroniseert dan alle inschrijvingen opnieuw om een eventuele deduplicatie van inschrijvingen uit te voeren.
 4. Bij vernieuwen van de inschrijvingen pagina voor een evenement worden de veranderingen weergegeven. (Deze synchronisatie kan lang duren, dus dit is niet meteen zichtbaar in de applicatie.)