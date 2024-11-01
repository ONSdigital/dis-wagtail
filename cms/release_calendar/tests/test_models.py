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
def test_release_calendar_page_table_of_contents_pre_published__content(rf, release_calendar_page, status):
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


@pytest.mark.parametrize(
    "status",
    [
        ReleaseStatus.PROVISIONAL,
        ReleaseStatus.CONFIRMED,
        ReleaseStatus.CANCELLED,
    ],
)
def test_release_calendar_page_table_of_contents_pre_published__census(rf, release_calendar_page, status):
    """Check TOC in a pre-published state shows about the data when is census."""
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

    expected = [{"url": "#summary", "text": "Summary"}, {"url": "#about-the-data", "text": "About the data"}]

    release_calendar_page.is_census = True
    release_calendar_page.is_accredited = False

    assert release_calendar_page.table_of_contents == expected
    assert release_calendar_page.get_context(request)["table_of_contents"] == expected


@pytest.mark.parametrize(
    "status",
    [
        ReleaseStatus.PROVISIONAL,
        ReleaseStatus.CONFIRMED,
        ReleaseStatus.CANCELLED,
    ],
)
def test_release_calendar_page__table_of_contents_pre_published__accredited(rf, release_calendar_page, status):
    """Check TOC in a pre-published state shows about the data when accredited."""
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

    expected = [{"url": "#summary", "text": "Summary"}, {"url": "#about-the-data", "text": "About the data"}]

    release_calendar_page.is_census = False
    release_calendar_page.is_accredited = True

    assert release_calendar_page.table_of_contents == expected
    assert release_calendar_page.get_context(request)["table_of_contents"] == expected


def test_release_calendar_page__table_of_contents_published(release_calendar_page):
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


@pytest.mark.parametrize(
    "status,shown",
    [
        (ReleaseStatus.PROVISIONAL, False),
        (ReleaseStatus.CONFIRMED, True),
        (ReleaseStatus.PUBLISHED, True),
        (ReleaseStatus.CANCELLED, True),
    ],
)
def test_release_calendar_page__table_of_contents__changes_to_release_date(release_calendar_page, status, shown):
    """Check TOC for the changes to release date if added. Should be there for non-provisional."""
    release_calendar_page.status = status
    release_calendar_page.changes_to_release_date = [
        {"type": "date_change_log", "value": {"previous_date": timezone.now(), "reason_for_change": "The reason"}}
    ]

    expected = {"url": "#changes-to-release-date", "text": "Changes to this release date"}
    assert (expected in release_calendar_page.table_of_contents) == shown


@pytest.mark.parametrize(
    "status,shown",
    [
        (ReleaseStatus.PROVISIONAL, False),
        (ReleaseStatus.CONFIRMED, True),
        (ReleaseStatus.PUBLISHED, True),
        (ReleaseStatus.CANCELLED, True),
    ],
)
def test_release_calendar_page__rendered__changes_to_release_date(client, release_calendar_page, status, shown):
    """Check rendered content for changes to release date. Should show for non-provisional."""
    release_calendar_page.status = status
    release_calendar_page.changes_to_release_date = [
        {"type": "date_change_log", "value": {"previous_date": timezone.now(), "reason_for_change": "The reason"}}
    ]
    release_calendar_page.save_revision().publish()

    response = client.get(release_calendar_page.url)

    assert ("The reason" in str(response.content)) == shown


@pytest.mark.parametrize(
    "status,shown",
    [
        (ReleaseStatus.PROVISIONAL, False),
        (ReleaseStatus.CONFIRMED, False),
        (ReleaseStatus.PUBLISHED, True),
        (ReleaseStatus.CANCELLED, False),
    ],
)
def test_release_calendar_page__table_of_contents__contact_details(release_calendar_page, status, shown):
    """Check TOC in a published state contains contact details if added."""
    release_calendar_page.status = status
    contact_details = ContactDetails(name="PSF team", email="psf@ons.gov.uk")
    contact_details.save()
    release_calendar_page.contact_details = contact_details

    expected = {"url": "#contact-details", "text": "Contact details"}
    assert (expected in release_calendar_page.table_of_contents) == shown


@pytest.mark.parametrize(
    "status,shown",
    [
        (ReleaseStatus.PROVISIONAL, False),
        (ReleaseStatus.CONFIRMED, False),
        (ReleaseStatus.PUBLISHED, True),
        (ReleaseStatus.CANCELLED, False),
    ],
)
def test_release_calendar_page__rendered__contact_details(client, release_calendar_page, status, shown):
    """Check rendered content for contact details."""
    release_calendar_page.status = status
    contact_details = ContactDetails(name="PSF team", email="psf@ons.gov.uk")
    contact_details.save()
    release_calendar_page.contact_details = contact_details
    release_calendar_page.save_revision().publish()

    response = client.get(release_calendar_page.url)

    assert ("PSF team" in str(response.content)) == shown


def test_release_calendar_page__table_of_contents_published__pre_release_access(release_calendar_page):
    """Check TOC in a published state has the pre-release access section if added."""
    release_calendar_page.status = ReleaseStatus.PUBLISHED
    release_calendar_page.pre_release_access = [{"type": "description", "value": "pre-release access notes"}]

    expected = [
        {"url": "#summary", "text": "Summary"},
        {"url": "#pre-release-access-list", "text": "Pre-release access list"},
    ]
    assert release_calendar_page.table_of_contents == expected


def test_release_calendar_page__table_of_contents_published__related_links(release_calendar_page):
    """Check TOC in a published state has the related links section if added."""
    release_calendar_page.status = ReleaseStatus.PUBLISHED
    # related links section
    related_link = ReleasePageRelatedLink(
        parent=release_calendar_page, link_url="https://ons.gov.uk", link_text="The link"
    )
    related_link.save()

    expected = [{"url": "#summary", "text": "Summary"}, {"url": "#links", "text": "You might also be interested in"}]
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
