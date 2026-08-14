from connectie import *
from modellen import *
from query_mapper import *

import os
from dotenv import load_dotenv

load_dotenv()
HOST = os.getenv("DB_host")
DB_NAAM = os.getenv("DB_name")
GEBRUIKERSNAAM = os.getenv("DB_username")
WACHTWOORD = os.getenv("DB_password")

if __name__ == "__main__":

    cat = Categorie("testcat", "test categorie")

    connectie = maak_connectie(HOST, DB_NAAM, GEBRUIKERSNAAM, WACHTWOORD)
    print(connectie)

    voer_query_uit(connectie, "INSERT INTO categorie (id, naam, alt_naam) VALUES (%s, %s, %s);", maak_categorie_query_arg(cat))

    sluit_connectie(connectie)
