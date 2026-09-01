"""Module die de modellen bijhoudt vereist voor logging

## Klassen:
    **LogLevel:** level van logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    **LogEntry:** log
"""
from django.db import models


class LogLevel(models.IntegerChoices):
    """Model dat de verschillende loglevels bijhoudt
    """
    DEBUG = 10, "Debug"
    INFO = 20, "Info"
    WARNING = 30, "Warning"
    ERROR = 40, "Error"
    CRITICAL = 50, "Critical"


class LogEntry(models.Model):
    """Model dat een log bijhoudt over Inschrijfbeheer
    """
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    level = models.PositiveSmallIntegerField(choices=LogLevel.choices, db_index=True)
    logger_name = models.CharField(max_length=255, db_index=True)
    message = models.TextField()
    module = models.CharField(max_length=255, blank=True)
    function = models.CharField(max_length=255, blank=True)
    line = models.PositiveIntegerField(null=True, blank=True)
    trace = models.TextField(blank=True)
    user_identifier = models.CharField(max_length=255, blank=True, db_index=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class WeezSynchronisatie(models.Model):
    """Model om bij te houden wanneer laatste synchronisatie met Weez gebeurde

    Attributes:
        tijdstip (datetime): tijdstip van synchronisatie
    """
    tijdstip = models.DateTimeField(primary_key=True, auto_now=True)

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = 'weez_sync'
