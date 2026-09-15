from procrastinate.contrib.django import app

@app.task
def synchroniseer_inschrijvingen_taak(evenement_id: str):
    pass

@app.task
def mail_attesten_taak():
    pass