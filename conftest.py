import logging

import pytest
from django.conf import settings
from django.core.files.base import ContentFile
from django.test import Client
from django.test.utils import override_settings
from wagtail.models import Page

from cms.documents.models import CustomDocument
from cms.home.models import HomePage
from cms.release_calendar.models import ReleaseCalendarIndex, ReleaseCalendarPage


@pytest.fixture(scope="session", autouse=True)
def _custom_media_dir_settings(tmpdir_factory):
    with override_settings(MEDIA_ROOT=str(tmpdir_factory.mktemp("media"))):
        yield


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


@pytest.fixture()
def root_page() -> Page:
    """Returns the root page. Useful for adding pages in tests."""
    return Page.objects.filter(depth=1).get()


@pytest.fixture()
def home_page() -> HomePage:
    """Returns the home page, which is created via a migration."""
    return HomePage.objects.first()


@pytest.fixture()
def release_calendar_index() -> ReleaseCalendarIndex:
    """Returns the release calendar index page, which is created via a migration."""
    return ReleaseCalendarIndex.objects.first()


@pytest.fixture()
def release_calendar_page(release_calendar_index) -> ReleaseCalendarPage:  # pylint: disable=redefined-outer-name
    """Returns a release calendar page."""
    page = ReleaseCalendarPage(title="The release", slug="the-release", summary="<p>about the release</p>")
    release_calendar_index.add_child(instance=page)
    page.save()

    return page


@pytest.fixture()
def document():
    """Creates a test document."""
    file = ContentFile("A boring example document", name="file.txt")
    return CustomDocument.objects.create(title="Test document", file=file)
