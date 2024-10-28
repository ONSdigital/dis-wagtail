import logging

import pytest
from django.conf import settings
from django.test import Client


@pytest.fixture
def enable_console_logging():
    """Fixture that re-enables console logging and ensures loggers propagate,
    so we can use the caplog pytest fixture.
    """
    original_logging = settings.LOGGING.copy()
    settings.LOGGING["handlers"]["console"] = {
        "level": "INFO",
        "class": "logging.StreamHandler",
    }
    for logger in settings.LOGGING["loggers"]:
        settings.LOGGING["loggers"][logger]["propagate"] = True

    logging.config.dictConfig(settings.LOGGING)

    yield

    logging.config.dictConfig(original_logging)


@pytest.fixture()
def csrf_check_client() -> Client:
    """A Django test client instance that enforces CSRF checks."""
    return Client(enforce_csrf_checks=True)
