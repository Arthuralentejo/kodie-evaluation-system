import logging

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core import logger as logger_module


def test_settings_normalizes_log_level() -> None:
    assert Settings(log_level="debug").log_level == "DEBUG"


def test_settings_rejects_invalid_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="loud")


def test_configure_logging_is_idempotent_and_uses_stdout_handler(monkeypatch) -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    try:
        root_logger.handlers = []
        monkeypatch.setattr(logger_module.settings, "log_level", "DEBUG")

        logger_module.configure_logging()
        logger_module.configure_logging()

        handler_names = [handler.get_name() for handler in root_logger.handlers]

        assert handler_names.count(logger_module.STDOUT_HANDLER_NAME) == 1
        assert root_logger.level == logging.DEBUG
        assert logger_module.get_logger("kodie.test").name == "kodie.test"
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)
