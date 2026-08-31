from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from budgetlens.config import Settings
from budgetlens.observability import sanitize_log_payload


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": "budgetlens-api",
            "environment": getattr(record, "environment", None),
            "event": getattr(record, "event", record.getMessage()),
            "trace_id": getattr(record, "trace_id", None),
            "request_id": getattr(record, "request_id", None),
            "organization_id_hash": getattr(record, "organization_id_hash", None),
            "user_id_hash": getattr(record, "user_id_hash", None),
            "outcome": getattr(record, "outcome", None),
            "route": getattr(record, "route", None),
            "method": getattr(record, "method", None),
            "status_class": getattr(record, "status_class", None),
            "failure_class": getattr(record, "failure_class", None),
        }
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        return json.dumps(sanitize_log_payload(payload))


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
