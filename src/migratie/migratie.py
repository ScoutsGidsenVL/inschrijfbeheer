from modellen import *

import os
from dotenv import load_dotenv

load_dotenv()
HOST = os.getenv("DB_host")
DB_NAAM = os.getenv("DB_name")
GEBRUIKERSNAAM = os.getenv("DB_username")
WACHTWOORD = os.getenv("DB_password")

if __name__ == "__main__":
    pass
