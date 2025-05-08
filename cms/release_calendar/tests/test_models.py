from http import HTTPStatus

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.blocks import StreamValue
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.core.custom_date_format import ons_date_format
from cms.core.models import ContactDetails
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


class ReleaseCalendarPageTestCase(WagtailTestUtils, TestCase):
    """Test Release CalendarPage model properties and logic."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.release_calendar_index = ReleaseCalendarIndex.objects.first()

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
                    f"templates/pages/release_calendar/release_calendar_page{suffix}",
                )

    def test_table_of_contents_pre_published__content(self):
        """Check table of contents in a pre-published state."""
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
                self.page.related_links = [
                    {
                        "type": "link",
                        "value": {"external_url": "https://ons.gov.uk", "title": "The link"},
                    }
                ]

                expected = [{"url": "#summary", "text": "Summary"}]

                self.assertListEqual(self.page.table_of_contents, expected)
                self.assertListEqual(self.page.get_context(self.request)["table_of_contents"], expected)

    def test_table_of_contents_pre_published__census(self):
        """Check table of contents in a pre-published state shows about the data when is census."""
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

                self.page.related_links = [
                    {
                        "type": "link",
                        "value": {"external_url": "https://ons.gov.uk", "title": "The link"},
                    }
                ]

                expected = [
                    {"url": "#summary", "text": "Summary"},
                    {"url": "#about-the-data", "text": "About the data"},
                ]

                self.page.is_census = True
                self.page.is_accredited = False

                self.assertListEqual(self.page.table_of_contents, expected)
                self.assertListEqual(self.page.get_context(self.request)["table_of_contents"], expected)

    def test_table_of_contents_pre_published__accredited(self):
        """Check table of contents in a pre-published state shows about the data when accredited."""
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
        """Check table of contents in a published state."""
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
        """Check table of contents for the changes to release date if added. Should be there for non-provisional."""
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
        """Check table of contents in a published state contains contact details if added."""
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
        """Check table of contents in a published state has the pre-release access section if added."""
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
        """Check table of contents in a published state has the related links section if added."""
        self.page.status = ReleaseStatus.PUBLISHED
        self.page.related_links = [{"type": "link", "value": {"url": "https://ons.gov.uk", "text": "The link"}}]

        self.assertListEqual(
            self.page.table_of_contents,
            [{"url": "#summary", "text": "Summary"}, {"url": "#links", "text": "You might also be interested in"}],
        )

    def test_delete_redirects_back_to_edit(self):
        """Test that we get redirected back to edit when trying to delete a release calendar page."""
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("wagtailadmin_pages:delete", args=(self.page.id,)),
            follow=True,
        )

        edit_url = reverse("wagtailadmin_pages:edit", args=(self.page.id,))
        self.assertRedirects(response, edit_url)

        self.assertIn(
            "Release Calendar pages cannot be deleted. You can mark them as cancelled instead.",
            [msg.message.strip() for msg in response.context["messages"]],
        )

        response = self.client.get(
            reverse("wagtailadmin_pages:delete", args=(self.page.id,)),
            follow=True,
        )
        self.assertRedirects(response, edit_url)

    def test_add_view_does_not_contain_the_bundle_note_panel(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse(
                "wagtailadmin_pages:add",
                args=("release_calendar", "releasecalendarpage", self.release_calendar_index.pk),
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response, "bundle-note")


class ReleaseCalendarPageRenderTestCase(TestCase):
    """Tests for rendered release calendar pages."""

    def setUp(self):
        self.page = ReleaseCalendarPageFactory()

    def test_rendered__content(self):
        """Check table of contents in a published state."""
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

    def test_release_date_text_overrides_release_datetime(self):
        """Check that if both release date and release date text are present,
        then release date text is used for provisional releases
        and release date is used for all other statuses.
        """
        cases = [
            (ReleaseStatus.PROVISIONAL, True),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, False),
        ]

        for status, expect_release_date_text in cases:
            with self.subTest(status=status, has_release_date_text=expect_release_date_text):
                self.page.status = status
                self.page.release_date = timezone.now()
                self.page.release_date_text = "January 2024"

                self.assertEqual(expect_release_date_text, self.page.release_date_value == "January 2024")
                self.assertEqual(
                    not expect_release_date_text,
                    self.page.release_date_value == ons_date_format(self.page.release_date, "DATETIME_FORMAT"),
                )

    def test_next_release_date_value_returns_next_release_date(self):
        """Check that if next release date and next release date text are present,
        then next release date is returned.
        """
        for status in [ReleaseStatus.PROVISIONAL, ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            with self.subTest(status=status):
                self.page.status = status

                next_release_date = timezone.now()
                self.page.next_release_date = next_release_date
                self.page.next_release_date_text = "November 2024"

                self.assertEqual(
                    self.page.next_release_date_value, ons_date_format(next_release_date, "DATETIME_FORMAT")
                )

    def test_next_release_date_value_returns_next_release_date_text(self):
        """Check that if only next release date text is present, then it is returned as next release date value."""
        for status in [ReleaseStatus.PROVISIONAL, ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            with self.subTest(status=status):
                self.page.status = status

                self.page.next_release_date = None
                self.page.next_release_date_text = "November 2024"

                self.assertEqual(self.page.next_release_date_value, "November 2024")

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
        """Check table of contents in a published state."""
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

    def test_rendered__datasets(self):
        """Check datasets are shown only in a published state."""
        lookup_dataset = Dataset.objects.create(
            namespace="LOOKUP",
            edition="lookup_edition",
            version="lookup_version",
            title="test lookup",
            description="lookup description",
        )
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, True),
            (ReleaseStatus.CANCELLED, False),
        ]
        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("dataset_lookup", lookup_dataset),
                ("manual_link", manual_dataset),
            ],
        )

        for status, is_shown in cases:
            with self.subTest(status=status, is_shown=is_shown):
                self.page.status = status
                self.page.save_revision().publish()

                response = self.client.get(self.page.url)

                self.assertEqual("Data" in str(response.content), is_shown)

                self.assertEqual(lookup_dataset.title in str(response.content), is_shown)
                self.assertEqual(lookup_dataset.description in str(response.content), is_shown)
                self.assertEqual(lookup_dataset.website_url in str(response.content), is_shown)

                self.assertEqual(manual_dataset["title"] in str(response.content), is_shown)
                self.assertEqual(manual_dataset["description"] in str(response.content), is_shown)
                self.assertEqual(manual_dataset["url"] in str(response.content), is_shown)

    def test_render_in_external_env(self):
        """Check calendar page renders in external env."""
        for status in ReleaseStatus:
            with self.subTest(status):
                self.page.status = status
                self.page.save_revision().publish()

                with override_settings(IS_EXTERNAL_ENV=True):
                    response = self.client.get(self.page.url)

                self.assertEqual(response.status_code, 200)


class ReleaseCalendarIndexTestCase(WagtailTestUtils, TestCase):
    """Tests for release calendar index."""

    def setUp(self):
        self.page = ReleaseCalendarIndex.objects.first()

    def test_delete_redirects_back_to_edit(self):
        """Test that we get redirected back to edit when trying to delete a release calendar index."""
        self.login()  # creates a superuser and logs them in
        delete_url = reverse("wagtailadmin_pages:delete", args=(self.page.id,))
        response = self.client.get(
            delete_url,
            follow=True,
        )

        self.assertRedirects(response, reverse("wagtailadmin_home"))

        self.assertIn(
            "The Release Calendar index cannot be deleted.",
            [msg.message.strip() for msg in response.context["messages"]],
        )

        edit_url = reverse("wagtailadmin_pages:edit", args=(self.page.id,))
        response = self.client.get(
            f"{delete_url}?next={edit_url}",
            follow=True,
        )
        self.assertRedirects(response, edit_url)

    def test_render(self):
        """Test that the index page renders."""
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_render_in_external_env(self):
        """Test that the index page renders in external environment."""
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
