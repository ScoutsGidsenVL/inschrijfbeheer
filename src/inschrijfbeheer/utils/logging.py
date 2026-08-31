"""Module die een handler geeft voor logging.
De logs worden weggeschreven naar de databank, zodat deze in Inschrijfbeheer zichtbaar zullen zijn.
"""
import logging
import traceback


class DatabaseLogHandler(logging.Handler):
    """Klasse die logging naar de databank toelaat
    """
    def emit(self, record):
        from inschrijfbeheer.models import LogEntry

        try:
            LogEntry.objects.using("logging").create(
                level=record.levelno,
                logger_name=record.name,
                message=self.format(record),
                module=record.module,
                function=record.funcName,
                line=record.lineno,
                trace=self._format_trace(record),
                user_identifier=getattr(record, "user_identifier", ""),
                extra=getattr(record, "extra_data", {}),
            )
        except Exception:
            self.handleError(record)

    def _format_trace(self, record):
        if record.exc_info:
            return "".join(traceback.format_exception(*record.exc_info))
        return ""