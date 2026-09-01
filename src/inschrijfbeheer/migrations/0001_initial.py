from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.RunSQL(
            "CREATE SEQUENCE IF NOT EXISTS evenement_vraag_id_seq;",
            "DROP SEQUENCE IF EXISTS evenement_vraag_id_seq;",
        ),
        migrations.RunSQL(
            "CREATE SEQUENCE IF NOT EXISTS inschrijving_vraagantwoord_id_seq;",
            "DROP SEQUENCE IF EXISTS inschrijving_vraagantwoord_id_seq;",
        ),
        migrations.RunSQL(
            "CREATE SEQUENCE IF NOT EXISTS deelnemer_id_seq;",
            "DROP SEQUENCE IF EXISTS deelnemer_id_seq;",
        ),
        migrations.RunSQL(
            "CREATE SEQUENCE IF NOT EXISTS inschrijving_id_seq;",
            "DROP SEQUENCE IF EXISTS inschrijving_id_seq;",
        ),
    ]