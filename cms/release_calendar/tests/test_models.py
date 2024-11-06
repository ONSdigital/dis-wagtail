from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.core.models import ContactDetails
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.models import ReleasePageRelatedLink
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


class ReleaseCalendarPageTestCase(WagtailTestUtils, TestCase):
    """Test Release CalendarPage model properties and logic."""

    def setUp(self):
        self.page = ReleaseCalendarPageFactory()

        # Request is created with each test to avoid mutation side effects
        self.request = RequestFactory().get("/")

    def test_template(self):
        """Check the template used."""
        cases = [
            (ReleaseStatus.PROVISIONAL, "--provisional.html"),
            (ReleaseStatus.CONFIRMED, "--confirmed.html"),
            (ReleaseStatus.CANCELLED, "--cancelled.html"),
            (ReleaseStatus.PUBLISHED, ".html"),
        ]
        for status, suffix in cases:
            with self.subTest(status=status, suffix=suffix):
                self.page.status = status
                self.assertEqual(
                    self.page.get_template(self.request),
                    f"templates/pages/release_calendar/release_calendar_page{ suffix }",
                )

    def test_related_links_for_context(self):
        """Check that the correct related links are passed to the context."""
        related_link = ReleasePageRelatedLink(parent=self.page, link_url="https://ons.gov.uk", link_text="The link")
        related_link.save()

        expected = [
            {"text": "The link", "url": "https://ons.gov.uk"},
        ]
        self.assertListEqual(self.page.related_links_for_context, expected)
        self.assertListEqual(self.page.get_context(self.request)["related_links"], expected)

    def test_table_of_contents_pre_published__content(self):
        """Check TOC in a pre-published state."""
        for status in [ReleaseStatus.PROVISIONAL, ReleaseStatus.CONFIRMED, ReleaseStatus.CANCELLED]:
            with self.subTest(status=status):
                self.page.status = status
                self.page.content = [
                    {
                        "type": "release_content",
                        "value": {
                            "title": "Publications",
                            "links": [{"external_url": "https://ons.gov.uk", "title": "test"}],
                        },
                    }
                ]

                related_link = ReleasePageRelatedLink(
                    parent=self.page, link_url="https://ons.gov.uk", link_text="The link"
                )
                related_link.save()

                expected = [{"url": "#summary", "text": "Summary"}]

                self.assertListEqual(self.page.table_of_contents, expected)
                self.assertListEqual(self.page.get_context(self.request)["table_of_contents"], expected)

    def test_table_of_contents_pre_published__census(self):
        """Check TOC in a pre-published state shows about the data when is census."""
        for status in [ReleaseStatus.PROVISIONAL, ReleaseStatus.CONFIRMED, ReleaseStatus.CANCELLED]:
            with self.subTest(status=status):
                self.page.status = status
                self.page.content = [
                    {
                        "type": "release_content",
                        "value": {
                            "title": "Publications",
                            "links": [{"external_url": "https://ons.gov.uk", "title": "test"}],
                        },
                    }
                ]

                related_link = ReleasePageRelatedLink(
                    parent=self.page, link_url="https://ons.gov.uk", link_text="The link"
                )
                related_link.save()

                expected = [
                    {"url": "#summary", "text": "Summary"},
                    {"url": "#about-the-data", "text": "About the data"},
                ]

                self.page.is_census = True
                self.page.is_accredited = False

                self.assertListEqual(self.page.table_of_contents, expected)
                self.assertListEqual(self.page.get_context(self.request)["table_of_contents"], expected)

    def test_table_of_contents_pre_published__accredited(self):
        """Check TOC in a pre-published state shows about the data when accredited."""
        for status in [ReleaseStatus.PROVISIONAL, ReleaseStatus.CONFIRMED, ReleaseStatus.CANCELLED]:
            with self.subTest(status=status):
                self.page.status = status
                self.page.content = [
                    {
                        "type": "release_content",
                        "value": {
                            "title": "Publications",
                            "links": [{"external_url": "https://ons.gov.uk", "title": "test"}],
                        },
                    }
                ]

                expected = [
                    {"url": "#summary", "text": "Summary"},
                    {"url": "#about-the-data", "text": "About the data"},
                ]

                self.page.is_census = False
                self.page.is_accredited = True

                self.assertListEqual(self.page.table_of_contents, expected)
                self.assertListEqual(self.page.get_context(self.request)["table_of_contents"], expected)

    def test_table_of_contents__published(self):
        """Check TOC in a published state."""
        self.page.status = ReleaseStatus.PUBLISHED
        self.page.content = [
            {
                "type": "release_content",
                "value": {
                    "title": "Publications",
                    "links": [{"type": "item", "value": {"external_url": "https://ons.gov.uk", "title": "test"}}],
                },
            }
        ]

        self.assertListEqual(
            self.page.table_of_contents,
            [
                {"url": "#summary", "text": "Summary"},
                {"url": "#publications", "text": "Publications"},
            ],
        )

    def test_table_of_contents__changes_to_release_date(self):
        """Check TOC for the changes to release date if added. Should be there for non-provisional."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, True),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, True),
        ]
        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status
                self.page.changes_to_release_date = [
                    {
                        "type": "date_change_log",
                        "value": {"previous_date": timezone.now(), "reason_for_change": "The reason"},
                    }
                ]

                expected = {"url": "#changes-to-release-date", "text": "Changes to this release date"}
                self.assertEqual(expected in self.page.table_of_contents, is_shown)
                del self.page.table_of_contents  # clear the cached property

    def test_table_of_contents__contact_details(self):
        """Check TOC in a published state contains contact details if added."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, False),
        ]
        contact_details = ContactDetails(name="PSF team", email="psf@ons.gov.uk")
        contact_details.save()
        self.page.contact_details = contact_details
        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status

                expected = {"url": "#contact-details", "text": "Contact details"}
                self.assertEqual(expected in self.page.table_of_contents, is_shown)
                del self.page.table_of_contents  # clear the cached property

    def test_table_of_contents__pre_release_access(self):
        """Check TOC in a published state has the pre-release access section if added."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, False),
        ]
        self.page.pre_release_access = [{"type": "description", "value": "pre-release access notes"}]
        expected = {"url": "#pre-release-access-list", "text": "Pre-release access list"}

        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status

                self.assertEqual(expected in self.page.table_of_contents, is_shown)
                del self.page.table_of_contents  # clear the cached property

    def test_table_of_contents_published__related_links(self):
        """Check TOC in a published state has the related links section if added."""
        self.page.status = ReleaseStatus.PUBLISHED
        # related links section
        related_link = ReleasePageRelatedLink(parent=self.page, link_url="https://ons.gov.uk", link_text="The link")
        related_link.save()

        self.assertListEqual(
            self.page.table_of_contents,
            [{"url": "#summary", "text": "Summary"}, {"url": "#links", "text": "You might also be interested in"}],
        )

    def test_releasepagerelated_links__clean_validates_page_or_link(self):
        """Check related links validation."""
        related = ReleasePageRelatedLink()
        with self.assertRaises(ValidationError) as info:
            related.clean()

        error = "You must specify link page or link url."
        assert info.exception.error_dict["link_page"][0].message == error
        assert info.exception.error_dict["link_url"][0].message == error

        related = ReleasePageRelatedLink(link_page=self.page, link_url="https://ons.gov.uk")
        with self.assertRaises(ValidationError) as info:
            related.clean()

        error = "You must specify link page or link url. You can't use both."
        assert info.exception.error_dict["link_page"][0].message == error
        assert info.exception.error_dict["link_url"][0].message == error

        related = ReleasePageRelatedLink(link_url="https://ons.gov.uk")
        with self.assertRaises(ValidationError) as info:
            related.clean()

        assert (
            info.exception.error_dict["link_text"][0].message
            == "You must specify link text, if you use the link url field."
        )

    def test_releasepagerelated_links__get_link_text(self):
        """Test the get_link_text method output."""
        related = ReleasePageRelatedLink(link_page=self.page)
        assert related.get_link_text() == self.page.title

        related = ReleasePageRelatedLink(link_page=self.page, link_text="The link")
        assert related.get_link_text() == "The link"

    def test_releasepagerelated_links__get_link_url(self):
        """Test the get_link_url method output."""
        related = ReleasePageRelatedLink(link_page=self.page)
        assert related.get_link_url() == self.page.url

        related = ReleasePageRelatedLink(link_url="https://ons.gov.uk")
        assert related.get_link_url() == "https://ons.gov.uk"

    def test_delete_redirects_back_to_edit(self):
        """Test that we get redirected back to edit when trying to delete a release calendar page."""
        self.login()  # creates a superuser and logs them in
        response = self.client.post(
            reverse("wagtailadmin_pages:delete", args=(self.page.id,)),
            follow=True,
        )

        edit_url = reverse("wagtailadmin_pages:edit", args=(self.page.id,))
        self.assertRedirects(response, edit_url)

        self.assertIn(
            "Release calendar pages cannot be deleted. You can mark them as cancelled instead.",
            [msg.message.strip() for msg in response.context["messages"]],
        )


class ReleaseCalendarPageRenderTestCase(TestCase):
    """Tests for rendered release calendar pages."""

    def setUp(self):
        self.page = ReleaseCalendarPageFactory()

    def test_rendered__content(self):
        """Check TOC in a published state."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, False),
        ]
        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status
                self.page.content = [
                    {
                        "type": "release_content",
                        "value": {
                            "title": "Publications",
                            "links": [
                                {
                                    "id": "123",
                                    "type": "item",
                                    "value": {"external_url": "https://ons.gov.uk", "title": "The publication link"},
                                }
                            ],
                        },
                    }
                ]
                self.page.save_revision().publish()

                response = self.client.get(self.page.url)

                self.assertEqual("The publication link" in str(response.content), is_shown)

    def test_rendered__changes_to_release_date(self):
        """Check rendered content for changes to release date. Should show for non-provisional."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, True),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, True),
        ]
        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status
                self.page.changes_to_release_date = [
                    {
                        "type": "date_change_log",
                        "value": {"previous_date": timezone.now(), "reason_for_change": "The reason"},
                    }
                ]
                self.page.save_revision().publish()

                response = self.client.get(self.page.url)

                self.assertEqual("The reason" in str(response.content), is_shown)

    def test_rendered__contact_details(self):
        """Check rendered content for contact details."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, False),
        ]

        contact_details = ContactDetails(name="PSF team", email="psf@ons.gov.uk")
        contact_details.save()
        self.page.contact_details = contact_details

        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status
                self.page.save_revision().publish()

                response = self.client.get(self.page.url)

                self.assertEqual("PSF team" in str(response.content), is_shown)

    def test_rendered__pre_release_access(self):
        """Check TOC in a published state."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, False),
        ]
        self.page.pre_release_access = [{"type": "description", "value": "pre-release access notes"}]

        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status
                self.page.save_revision().publish()

                response = self.client.get(self.page.url)

                self.assertEqual("pre-release access notes" in str(response.content), is_shown)
