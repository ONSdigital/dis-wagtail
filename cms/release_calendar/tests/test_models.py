from http import HTTPStatus
from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.blocks import StreamValue
from wagtail.locks import BasicLock
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory
from cms.core.custom_date_format import ons_date_format, ons_default_datetime
from cms.core.models import ContactDetails
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.locks import ReleasePageInBundleReadyToBePublishedLock
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


class ReleaseCalendarPageModelTestCase(WagtailTestUtils, TestCase):
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

                expected = [
                    {
                        "url": "#summary",
                        "text": "Summary",
                        "attributes": {
                            "data-ga-event": "navigation-onpage",
                            "data-ga-navigation-type": "table-of-contents",
                            "data-ga-section-title": "Summary",
                        },
                    }
                ]

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
                    {
                        "url": "#summary",
                        "text": "Summary",
                        "attributes": {
                            "data-ga-event": "navigation-onpage",
                            "data-ga-navigation-type": "table-of-contents",
                            "data-ga-section-title": "Summary",
                        },
                    },
                    {
                        "url": "#about-the-data",
                        "text": "About the data",
                        "attributes": {
                            "data-ga-event": "navigation-onpage",
                            "data-ga-navigation-type": "table-of-contents",
                            "data-ga-section-title": "About the data",
                        },
                    },
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
                    {
                        "url": "#summary",
                        "text": "Summary",
                        "attributes": {
                            "data-ga-event": "navigation-onpage",
                            "data-ga-navigation-type": "table-of-contents",
                            "data-ga-section-title": "Summary",
                        },
                    },
                    {
                        "url": "#about-the-data",
                        "text": "About the data",
                        "attributes": {
                            "data-ga-event": "navigation-onpage",
                            "data-ga-navigation-type": "table-of-contents",
                            "data-ga-section-title": "About the data",
                        },
                    },
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
                {
                    "url": "#summary",
                    "text": "Summary",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Summary",
                    },
                },
                {
                    "url": "#publications",
                    "text": "Publications",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Publications",
                    },
                },
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

                expected = {
                    "url": "#changes-to-release-date",
                    "text": "Changes to this release date",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Changes to this release date",
                    },
                }
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

                expected = {
                    "url": "#contact-details",
                    "text": "Contact details",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Contact details",
                    },
                }
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
        expected = {
            "url": "#pre-release-access-list",
            "text": "Pre-release access list",
            "attributes": {
                "data-ga-event": "navigation-onpage",
                "data-ga-navigation-type": "table-of-contents",
                "data-ga-section-title": "Pre-release access list",
            },
        }

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
            [
                {
                    "url": "#summary",
                    "text": "Summary",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "Summary",
                    },
                },
                {
                    "url": "#links",
                    "text": "You might also be interested in",
                    "attributes": {
                        "data-ga-event": "navigation-onpage",
                        "data-ga-navigation-type": "table-of-contents",
                        "data-ga-section-title": "You might also be interested in",
                    },
                },
            ],
        )

    def test_get_lock(self):
        self.assertIsNone(self.page.get_lock())

        self.page.locked = True
        self.assertIsInstance(self.page.get_lock(), BasicLock)

    def test_get_lock_when_linked_with_bundle_ready_to_be_published(self):
        BundleFactory(release_calendar_page=self.page, status=BundleStatus.APPROVED)
        self.assertIsInstance(self.page.get_lock(), ReleasePageInBundleReadyToBePublishedLock)


class ReleaseCalendarPageAdminTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser("admin")
        cls.release_calendar_page = ReleaseCalendarPageFactory()
        cls.release_calendar_index = cls.release_calendar_page.get_parent()
        cls.edit_url = reverse("wagtailadmin_pages:edit", args=[cls.release_calendar_page.pk])
        cls.add_url = reverse(
            "wagtailadmin_pages:add",
            args=("release_calendar", "releasecalendarpage", cls.release_calendar_index.pk),
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_date_placeholder_on_edit_form(self):
        """Test that the date input field displays date placeholder."""
        response = self.client.get(self.add_url)

        content = response.content.decode(encoding="utf-8")
        self.assertInHTML(
            (
                '<input type="text" name="next_release_date" autocomplete="off" '
                'placeholder="YYYY-MM-DD HH:MM" id="id_next_release_date">'
            ),
            content,
        )

    def test_default_date_on_release_date(self):
        """Test release date shows a default datetime from ons_default_datetime."""
        response = self.client.get(self.add_url, follow=True)

        content = response.content.decode(encoding="utf-8")

        default_datetime = ons_default_datetime().strftime("%Y-%m-%d %H:%M")

        self.assertInHTML(
            (
                f'<input type="text" name="release_date" value="{default_datetime}" autocomplete="off" '
                f'placeholder="YYYY-MM-DD HH:MM" required id="id_release_date">'
            ),
            content,
        )

    def test_preview_mode_url(self):
        """Tests preview pages with preview mode loads."""
        cases = {
            ReleaseStatus.PROVISIONAL: "This release is not yet",
            ReleaseStatus.CONFIRMED: "This release is not yet",
            ReleaseStatus.PUBLISHED: "The publication link",
            ReleaseStatus.CANCELLED: "Cancelled for reasons",
        }

        post_data = nested_form_data(
            {
                "title": self.release_calendar_page.title,
                "slug": self.release_calendar_page.slug,
                "status": self.release_calendar_page.status,
                "release_date": self.release_calendar_page.release_date,
                "summary": rich_text(self.release_calendar_page.summary),
                "notice": rich_text("Cancelled for reasons"),
                "content": streamfield(
                    [
                        (
                            "release_content",
                            {
                                "title": "Publications",
                                "links": streamfield(
                                    [
                                        (
                                            "item",
                                            {"external_url": "https://ons.gov.uk", "title": "The publication link"},
                                        )
                                    ]
                                ),
                            },
                        )
                    ]
                ),
                "changes_to_release_date": streamfield([]),
                "pre_release_access": streamfield([]),
                "related_links": streamfield([]),
                "datasets": streamfield([]),
            }
        )

        preview_url_base = reverse("wagtailadmin_pages:preview_on_edit", args=[self.release_calendar_page.pk])
        for mode, lookup in cases.items():
            with self.subTest(mode=mode):
                preview_url = f"{preview_url_base}?mode={mode}"
                response = self.client.post(preview_url, post_data)
                self.assertEqual(response.status_code, 200)
                self.assertJSONEqual(
                    response.content.decode(),
                    {"is_valid": True, "is_available": True},
                )

                response = self.client.get(preview_url)
                self.assertContains(response, lookup)

    def test_delete_redirects_back_to_edit(self):
        """Test that we get redirected back to edit when trying to delete a release calendar page."""
        delete_url = reverse("wagtailadmin_pages:delete", args=(self.release_calendar_page.id,))
        response = self.client.post(delete_url, follow=True)

        self.assertRedirects(response, self.edit_url)
        self.assertIn(
            "Release Calendar pages cannot be deleted. You can mark them as cancelled instead.",
            [msg.message.strip() for msg in response.context["messages"]],
        )

        response = self.client.get(delete_url, follow=True)
        self.assertRedirects(response, self.edit_url)

    def test_add_view_does_not_contain_the_bundle_note_panel(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response, "bundle-note")

    def test_page_locked_if_in_bundle_ready_to_be_published(self):
        bundle = BundleFactory(release_calendar_page=self.release_calendar_page, status=BundleStatus.APPROVED)

        response = self.client.get(self.edit_url)
        self.assertContains(
            response,
            "This release calendar page is linked to a bundle that is ready to be published. "
            "You must unlink them in order to make changes.",
        )
        self.assertContains(response, "Manage bundle")
        self.assertContains(response, reverse("bundle:edit", args=[bundle.pk]))

    @patch("cms.release_calendar.locks.user_can_manage_bundles", return_value=False)
    @patch("cms.release_calendar.panels.user_can_manage_bundles", return_value=False)
    @patch("cms.bundles.panels.user_can_manage_bundles", return_value=False)
    def test_page_locked_if_in_bundle_ready_to_be_published_but_user_cannot_manage_bundles(self, _mock, _mock2, _mock3):
        # note: we are mocking user_can_manage_bundles in all entry points.
        bundle = BundleFactory(release_calendar_page=self.release_calendar_page, status=BundleStatus.APPROVED)

        response = self.client.get(self.edit_url)
        self.assertContains(
            response,
            "This release calendar page is linked to a bundle that is ready to be published. "
            "You must unlink them in order to make changes.",
        )
        self.assertNotContains(response, "Manage bundle")
        self.assertNotContains(response, reverse("bundle:edit", args=[bundle.pk]))


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

    def test_rendered__statistics_badge_url(self):
        """Check statistics badge URL is rendered correctly."""
        self.page.is_accredited = True
        self.page.save_revision().publish()

        cases = [ReleaseStatus.PROVISIONAL, ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED, ReleaseStatus.CANCELLED]
        expected_url = (
            "https://uksa.statisticsauthority.gov.uk/"
            + "about-the-authority/uk-statistical-system/types-of-official-statistics/"
        )

        for status in cases:
            with self.subTest(status=status, expected_url=expected_url):
                self.page.status = status
                self.page.save_revision().publish()

                response = self.client.get(self.page.url)

                self.assertContains(response, expected_url)

    def test_rendered__datasets(self):
        """Check datasets are shown only in a published state."""
        lookup_dataset = Dataset.objects.create(
            namespace="LOOKUP",
            edition="lookup_edition",
            version=1,
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
                self.assertEqual(lookup_dataset.url_path in str(response.content), is_shown)

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

    def test_rendered__release_date_label_for_provisional(self):
        """Check that provisional pages show 'Provisional release date:' label."""
        self.page.status = ReleaseStatus.PROVISIONAL
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(response, "Provisional release date:")
        self.assertNotContains(response, "Release date:")

    def test_rendered__release_date_label_for_non_provisional(self):
        """Check that non-provisional pages show 'Release date:' label."""
        cases = [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED, ReleaseStatus.CANCELLED]

        for status in cases:
            with self.subTest(status=status):
                self.page.status = status
                self.page.save_revision().publish()

                response = self.client.get(self.page.url)

                self.assertContains(response, "Release date:")
                self.assertNotContains(response, "Provisional release date:")


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
