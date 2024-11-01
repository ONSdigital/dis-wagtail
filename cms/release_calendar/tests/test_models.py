import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from cms.core.models import ContactDetails
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.models import ReleasePageRelatedLink

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "status,suffix",
    [
        (ReleaseStatus.PROVISIONAL, "--provisional.html"),
        (ReleaseStatus.CONFIRMED, "--confirmed.html"),
        (ReleaseStatus.CANCELLED, "--cancelled.html"),
        (ReleaseStatus.PUBLISHED, ".html"),
    ],
)
def test_release_calendar_page_template(rf, release_calendar_page, status, suffix):
    """Check the template used."""
    request = rf.get("/")
    release_calendar_page.status = status
    assert (
        release_calendar_page.get_template(request)
        == f"templates/pages/release_calendar/release_calendar_page{ suffix }"
    )


def test_release_calendar_page_related_links_for_context(rf, release_calendar_page):
    """Check that the correct related links are passed to the context."""
    request = rf.get("/")
    related_link = ReleasePageRelatedLink(
        parent=release_calendar_page, link_url="https://ons.gov.uk", link_text="The link"
    )
    related_link.save()

    expected = [
        {"text": "The link", "url": "https://ons.gov.uk"},
    ]
    assert release_calendar_page.related_links_for_context == expected
    assert release_calendar_page.get_context(request)["related_links"] == expected


@pytest.mark.parametrize(
    "status",
    [
        ReleaseStatus.PROVISIONAL,
        ReleaseStatus.CONFIRMED,
        ReleaseStatus.CANCELLED,
    ],
)
def test_release_calendar_page_table_of_contents_pre_published(rf, release_calendar_page, status):
    """Check TOC in a pre-published state."""
    request = rf.get("/")
    release_calendar_page.status = status
    release_calendar_page.content = [
        {
            "type": "release_content",
            "value": {"title": "Publications", "links": [{"external_url": "https://ons.gov.uk", "title": "test"}]},
        }
    ]

    related_link = ReleasePageRelatedLink(
        parent=release_calendar_page, link_url="https://ons.gov.uk", link_text="The link"
    )
    related_link.save()

    expected = [{"url": "#summary", "text": "Summary"}]
    assert release_calendar_page.table_of_contents == expected
    assert release_calendar_page.get_context(request)["table_of_contents"] == expected

    expected_with_census_or_accredited = [*expected, {"url": "#about-the-data", "text": "About the data"}]

    del release_calendar_page.table_of_contents  # clear the cached property
    release_calendar_page.is_census = True
    release_calendar_page.is_accredited = False

    assert release_calendar_page.table_of_contents == expected_with_census_or_accredited
    assert release_calendar_page.get_context(request)["table_of_contents"] == expected_with_census_or_accredited

    del release_calendar_page.table_of_contents  # clear the cached property
    release_calendar_page.is_census = False
    release_calendar_page.is_accredited = True

    assert release_calendar_page.table_of_contents == expected_with_census_or_accredited
    assert release_calendar_page.get_context(request)["table_of_contents"] == expected_with_census_or_accredited


def test_release_calendar_page_table_of_contents_published(release_calendar_page):
    """Check TOC in a published state."""
    release_calendar_page.status = ReleaseStatus.PUBLISHED
    release_calendar_page.content = [
        {
            "type": "release_content",
            "value": {
                "title": "Publications",
                "links": [{"type": "item", "value": {"external_url": "https://ons.gov.uk", "title": "test"}}],
            },
        }
    ]

    expected = [
        {"url": "#summary", "text": "Summary"},
        {"url": "#publications", "text": "Publications"},
    ]
    assert release_calendar_page.table_of_contents == expected

    # changes to the release date section
    release_calendar_page.changes_to_release_date = [
        {"type": "date_change_log", "value": {"previous_date": timezone.now(), "reason_for_change": "The reason"}}
    ]

    del release_calendar_page.table_of_contents  # clear the cached property
    expected += [{"url": "#changes-to-release-date", "text": "Changes to this release date"}]
    assert release_calendar_page.table_of_contents == expected

    # contact details section
    contact_details = ContactDetails(name="PSF team", email="psf@ons.gov.uk")
    contact_details.save()
    release_calendar_page.contact_details = contact_details

    del release_calendar_page.table_of_contents  # clear the cached property
    expected += [{"url": "#contact-details", "text": "Contact details"}]
    assert release_calendar_page.table_of_contents == expected

    # pre-release section
    release_calendar_page.pre_release_access = [{"type": "description", "value": "pre-release access notes"}]

    del release_calendar_page.table_of_contents  # clear the cached property
    expected += [{"url": "#pre-release-access-list", "text": "Pre-release access list"}]
    assert release_calendar_page.table_of_contents == expected

    # related links section
    related_link = ReleasePageRelatedLink(
        parent=release_calendar_page, link_url="https://ons.gov.uk", link_text="The link"
    )
    related_link.save()

    del release_calendar_page.table_of_contents  # clear the cached property
    del release_calendar_page.related_links_for_context  # clear the cached property
    expected += [{"url": "#links", "text": "You might also be interested in"}]
    assert release_calendar_page.table_of_contents == expected


def test_releasepagerelated_links__clean_validates_page_or_link(release_calendar_page):
    """Check related links validation."""
    related = ReleasePageRelatedLink()
    with pytest.raises(ValidationError) as info:
        related.clean()

    error = "You must specify link page or link url."
    assert info.value.error_dict["link_page"][0].message == error
    assert info.value.error_dict["link_url"][0].message == error

    related = ReleasePageRelatedLink(link_page=release_calendar_page, link_url="https://ons.gov.uk")
    with pytest.raises(ValidationError) as info:
        related.clean()

    error = "You must specify link page or link url. You can't use both."
    assert info.value.error_dict["link_page"][0].message == error
    assert info.value.error_dict["link_url"][0].message == error

    related = ReleasePageRelatedLink(link_url="https://ons.gov.uk")
    with pytest.raises(ValidationError) as info:
        related.clean()

    assert info.value.error_dict["link_text"][0].message == "You must specify link text, if you use the link url field."


def test_releasepagerelated_links__get_link_text(release_calendar_page):
    """Test the get_link_text method output."""
    related = ReleasePageRelatedLink(link_page=release_calendar_page)
    assert related.get_link_text() == release_calendar_page.title

    related = ReleasePageRelatedLink(link_page=release_calendar_page, link_text="The link")
    assert related.get_link_text() == "The link"


def test_releasepagerelated_links__get_link_url(release_calendar_page):
    """Test the get_link_url method output."""
    related = ReleasePageRelatedLink(link_page=release_calendar_page)
    assert related.get_link_url() == release_calendar_page.url

    related = ReleasePageRelatedLink(link_url="https://ons.gov.uk")
    assert related.get_link_url() == "https://ons.gov.uk"
