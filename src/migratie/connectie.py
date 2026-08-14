from psycopg2 import connect

from modellen import *

def maak_connectie(host: str, database: str, username:str, password: str):
    return connect(host=host, database=database, user=username, password=password)

def sluit_connectie(connectie) -> None:
    connectie.close()

def voer_query_uit(connectie, query: str, argumenten: tuple | None = None) -> bool:
    cursor = connectie.cursor()

    if argumenten:
        cursor.execute(query, argumenten)
    else:
        cursor.execute(query)

    connectie.commit()