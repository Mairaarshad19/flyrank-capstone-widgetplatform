"""
Structured (JSON) logging setup.

Plain `print()` statements are the #1 reason "it broke in prod and nobody knows
why." Every log line here is a JSON object with a timestamp, level, logger name,
and message, plus whatever `extra` fields a call site attaches (request_id,
tenant_id, widget_id, etc). That makes logs greppable and, later, pipeable into
any log aggregator without touching this file again.
"""
import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings

RESERVED_LOG_RECORD_KEYS = set(logging.makeLogRecord({}).__dict__.keys())


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Pull in any structured extras the call site attached, e.g.
        # logger.info("submission_stored", extra={"widget_id": id, "tenant_id": t})
        for key, value in record.__dict__.items():
            if key not in RESERVED_LOG_RECORD_KEYS and key != "message":
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)

    # Quiet down noisy third-party loggers unless we're actively debugging them.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
