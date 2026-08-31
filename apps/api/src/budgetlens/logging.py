from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from budgetlens.config import Settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": "budgetlens-api",
            "environment": getattr(record, "environment", None),
            "event": getattr(record, "event", record.getMessage()),
            "trace_id": getattr(record, "trace_id", None),
            "outcome": getattr(record, "outcome", None),
        }
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        return json.dumps({key: value for key, value in payload.items() if value is not None})


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.app_log_level)

    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
