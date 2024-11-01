import pytest
from django.utils import timezone
from wagtail.test.utils.form_data import inline_formset, nested_form_data, rich_text, streamfield

from cms.release_calendar.enums import NON_PROVISIONAL_STATUS_CHOICES, ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarPage

pytestmark = pytest.mark.django_db

FORM_CLASS = ReleaseCalendarPage.get_edit_handler().get_form_class()  # pylint: disable=no-member


def raw_form_data(release_calendar_page):
    """Returns raw form data."""
    return {
        # required fields
        "title": release_calendar_page.title,
        "slug": release_calendar_page.slug,
        "summary": rich_text(release_calendar_page.summary),
        "content": streamfield([]),
        "changes_to_release_date": streamfield([]),
        "pre_release_access": streamfield([]),
        # our values
        "status": ReleaseStatus.PROVISIONAL,
        "notice": '{"entityMap": {},"blocks": []}',  # an empty rich text
        "related_links": inline_formset([]),
    }


def form_data(release_calendar_page):
    """Returns properly nested form data, as expected on submission."""
    return nested_form_data(raw_form_data(release_calendar_page))


@pytest.mark.parametrize(
    "status,choices",
    [
        (ReleaseStatus.PROVISIONAL, ReleaseStatus.choices),
        (ReleaseStatus.CONFIRMED, NON_PROVISIONAL_STATUS_CHOICES),
        (ReleaseStatus.CANCELLED, NON_PROVISIONAL_STATUS_CHOICES),
        (ReleaseStatus.PUBLISHED, NON_PROVISIONAL_STATUS_CHOICES),
    ],
)
def test_release_calendar_form_init__status_choices(release_calendar_page, status, choices):
    """Checks that when the release entry is non-provisional, the provisional state is not a choice."""
    release_calendar_page.status = status
    form = FORM_CLASS(instance=release_calendar_page)

    assert form.fields["status"].choices == choices


@pytest.mark.parametrize(
    "status,disabled",
    [
        (ReleaseStatus.PROVISIONAL, False),
        (ReleaseStatus.CONFIRMED, False),
        (ReleaseStatus.CANCELLED, False),
        (ReleaseStatus.PUBLISHED, True),
    ],
)
def test_release_calendar_form_init__release_date_disabled(release_calendar_page, status, disabled):
    """Checks that the release_date field is disabled when the status is published."""
    release_calendar_page.status = status
    form = FORM_CLASS(instance=release_calendar_page)

    assert form.fields["release_date"].disabled == disabled


def test_release_calendar_form__clean__happy_path(release_calendar_page):
    """Checks the release calendar admin form doesn't complain when good data is submitted."""
    data = form_data(release_calendar_page)
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() is True


def test_release_calendar_page_form__clean__validates_notice(release_calendar_page):
    """Checks that there is a notice if cancelling."""
    data = form_data(release_calendar_page)
    data["status"] = ReleaseStatus.CANCELLED
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() is False
    assert form.errors["notice"] == ["The notice field is required when the release is cancelled"]


@pytest.mark.parametrize(
    "status,is_valid",
    [
        (ReleaseStatus.PROVISIONAL, True),
        (ReleaseStatus.CANCELLED, True),
        (ReleaseStatus.CONFIRMED, False),
        (ReleaseStatus.PUBLISHED, False),
    ],
)
def test_release_calendar_form__clean__validates_release_date_when_confirmed(release_calendar_page, status, is_valid):
    """Validates that the release date must be set if the release is confirmed."""
    data = form_data(release_calendar_page)
    data["status"] = status
    data["notice"] = rich_text("")
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() == is_valid
    if not is_valid:
        assert form.errors["release_date"] == ["The release date field is required when the release is confirmed"]


@pytest.mark.parametrize(
    "text, is_valid",
    [
        ("November 2024", True),
        ("Nov 2024", False),
        ("November 24", False),
        ("November 2024 to December 2024", True),
        ("November 2024 to infinity", False),
        ("November 2024 to December 2024 to January 2025", False),
    ],
)
def test_release_calendar_form__clean__validates_release_date_text(release_calendar_page, text, is_valid):
    """Validates that the release date text format."""
    data = form_data(release_calendar_page)
    data["release_date_text"] = text
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() == is_valid
    if not is_valid:
        assert form.errors["release_date_text"] == [
            "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format."
        ]


def test_release_calendar_form__clean__validates_release_date_text_start_end_dates(release_calendar_page):
    """Validates that the release date text with start and end month make sense."""
    data = form_data(release_calendar_page)
    data["release_date_text"] = "November 2024 to September 2024"
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() is False
    assert form.errors["release_date_text"] == ["The end month must be after the start month."]


def test_release_calendar_form__clean__adding_a_release_date_when_confirming(release_calendar_page):
    """Checks that we can set a new release date when the release is confirmed, if previously it was empty."""
    release_calendar_page.release_date = None

    data = form_data(release_calendar_page)
    data["release_date"] = timezone.now()
    data["status"] = ReleaseStatus.CONFIRMED

    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid()


@pytest.mark.parametrize("status", [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED])
def test_release_calendar_form__clean__validates_changes_to_release_date_must_be_filled(release_calendar_page, status):
    """Checks that one must add data to changes_to_release_date if the confirmed release data changes."""
    release_calendar_page.release_date = timezone.now()
    data = form_data(release_calendar_page)
    data["release_date"] = timezone.now()
    data["status"] = status
    data["notice"] = rich_text("")
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() is False
    assert form.errors["changes_to_release_date"] == [
        "If a confirmed calendar entry needs to be rescheduled, the 'Changes to release date' field must be filled out."
    ]


@pytest.mark.parametrize("status", [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED])
def test_release_calendar_form__clean__validates_changes_to_release_date_cannot_be_removed(
    release_calendar_page, status
):
    """Tests that one cannot remove changes_to_release_date data."""
    release_calendar_page.changes_to_release_date = [
        {"type": "date_change_log", "value": {"previous_date": timezone.now(), "reason_for_change": "The reason"}}
    ]
    data = raw_form_data(release_calendar_page)
    data["status"] = status
    data["notice"] = rich_text("")
    data["release_date"] = timezone.now()
    data["changes_to_release_date"] = streamfield([])
    data = nested_form_data(data)
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() is False
    assert form.errors["changes_to_release_date"] == ["You cannot remove entries from the 'Changes to release date'."]


@pytest.mark.parametrize("status", [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED])
def test_release_calendar_form__clean__validates_release_date_when_confirmed__happy_path(release_calendar_page, status):
    """Checks that there are no errors when good data is submitted."""
    data = raw_form_data(release_calendar_page)
    data["status"] = status
    data["notice"] = rich_text("")
    data["release_date"] = timezone.now()
    data["changes_to_release_date"] = streamfield(
        [("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "The reason"})]
    )
    data = nested_form_data(data)
    form = FORM_CLASS(instance=release_calendar_page, data=data)

    assert form.is_valid() is True
