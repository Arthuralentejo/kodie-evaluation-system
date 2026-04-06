import json
import hashlib
import logging
import sys
from datetime import date, datetime
from typing import Any

from app.core.config import settings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
STDOUT_HANDLER_NAME = "kodie.stdout"


def _resolve_log_level() -> int:
    return logging.getLevelNamesMapping()[settings.log_level]


def configure_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    log_level = _resolve_log_level()

    stdout_handler = next(
        (handler for handler in root_logger.handlers if handler.get_name() == STDOUT_HANDLER_NAME),
        None,
    )
    if stdout_handler is None:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.set_name(STDOUT_HANDLER_NAME)
        root_logger.addHandler(stdout_handler)

    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.setLevel(log_level)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def hash_identifier(value: Any | None) -> str | None:
    if value is None:
        return None

    raw_value = str(value).strip()
    if not raw_value:
        return None

    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()[:12]


def _serialize_log_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return json.dumps(value.isoformat(), ensure_ascii=True)
    if isinstance(value, (list, tuple, set)):
        return json.dumps(list(value), ensure_ascii=True, default=str, separators=(",", ":"))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True, default=str, separators=(",", ":"), sort_keys=True)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def build_log_message(event: str, **fields: Any) -> str:
    serialized_fields = [
        f"{key}={_serialize_log_value(value)}"
        for key, value in fields.items()
        if value is not None
    ]
    if not serialized_fields:
        return event
    return f"{event} {' '.join(serialized_fields)}"
