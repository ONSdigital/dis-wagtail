from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.enums import NON_PROVISIONAL_STATUS_CHOICES, ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarPage
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


class ReleaseCalendarPageAdminFormTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

    def setUp(self):
        self.page = ReleaseCalendarPageFactory()
        self.form_class = ReleaseCalendarPage.get_edit_handler().get_form_class()  # pylint: disable-all
        self.form_data = nested_form_data(self.raw_form_data())

    def raw_form_data(self, page=None):
        """Returns raw form data."""
        the_page = page or self.page
        return {
            # required fields
            "title": the_page.title,
            "slug": the_page.slug,
            "release_date": timezone.now(),
            "summary": rich_text(the_page.summary),
            "content": streamfield([]),
            "changes_to_release_date": streamfield([]),
            "pre_release_access": streamfield([]),
            # our values
            "status": ReleaseStatus.PROVISIONAL,
            "notice": '{"entityMap": {},"blocks": []}',  # an empty rich text
            "related_links": streamfield([]),
            "datasets": streamfield([]),
        }

    def test_form_init__status_choices(self):
        """Checks that when the release entry is non-provisional, the provisional state is not a choice."""
        cases = [
            (ReleaseStatus.PROVISIONAL, ReleaseStatus.choices),
            (ReleaseStatus.CONFIRMED, NON_PROVISIONAL_STATUS_CHOICES),
            (ReleaseStatus.CANCELLED, NON_PROVISIONAL_STATUS_CHOICES),
            (ReleaseStatus.PUBLISHED, NON_PROVISIONAL_STATUS_CHOICES),
        ]
        for status, choices in cases:
            with self.subTest(status=status, choices=choices):
                self.page.status = status
                form = self.form_class(instance=self.page)

                self.assertEqual(form.fields["status"].choices, choices)

    def test_form_init__release_date_disabled(self):
        """Checks that the release_date field is disabled when the status is published."""
        cases = [
            (ReleaseStatus.PROVISIONAL, False),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.CANCELLED, False),
            (ReleaseStatus.PUBLISHED, True),
        ]
        for status, is_disabled in cases:
            with self.subTest(status=status, is_disabled=is_disabled):
                self.page.status = status
                form = self.form_class(instance=self.page)

                self.assertEqual(form.fields["release_date"].disabled, is_disabled)

    def test_form_clean__happy_path(self):
        """Checks the release calendar admin form doesn't complain when good data is submitted."""
        form = self.form_class(instance=self.page, data=self.form_data)

        self.assertTrue(form.is_valid())

    def test_form_clean__validates_notice(self):
        """Checks that there is a notice if cancelling."""
        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        self.assertFormError(form, "notice", ["The notice field is required when the release is cancelled"])

    def test_form_clean__validates_release_date_is_mandatory(self):
        """Validates that the release date must be set on all."""
        data = self.form_data

        for status in ReleaseStatus:
            with self.subTest(status=status):
                data["status"] = status
                data["notice"] = rich_text("")
                form = self.form_class(instance=self.page, data=data)

                self.assertEqual(form.is_valid(), True)

    def test_form_clean__validates_release_date_text(self):
        """Validates that the release date text format."""
        data = self.form_data
        cases = [
            ("November 2024", True),
            ("Nov 2024", False),
            ("November 24", False),
            ("November 2024 to December 2024", True),
            ("November 2024 to infinity", False),
            ("November 2024 to December 2024 to January 2025", False),
        ]
        for text, is_valid in cases:
            with self.subTest(text=text, is_valid=is_valid):
                data["release_date_text"] = text
                form = self.form_class(instance=self.page, data=data)

                self.assertEqual(form.is_valid(), is_valid)
                if not is_valid:
                    self.assertFormError(
                        form,
                        "release_date_text",
                        ["The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format."],
                    )

    def test_form_clean__validates_release_date_text_start_end_dates(self):
        """Validates that the release date text with start and end month make sense."""
        data = self.form_data

        data["release_date_text"] = "November 2024 to September 2024"
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        self.assertFormError(form, "release_date_text", ["The end month must be after the start month."])

    def test_form_clean__can_add_release_date_when_confirming(self):
        """Checks that we can set a new release date when the release is confirmed, if previously it was empty."""
        self.page.release_date = None

        data = self.form_data
        data["release_date"] = timezone.now()
        data["status"] = ReleaseStatus.CONFIRMED

        form = self.form_class(instance=self.page, data=data)

        self.assertTrue(form.is_valid())

    def test_form_clean__validates_changes_to_release_date_must_be_filled(self):
        """Checks that one must add data to changes_to_release_date if the confirmed release data changes."""
        self.page.status = ReleaseStatus.CONFIRMED
        data = self.form_data
        data["notice"] = rich_text("")

        for status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            with self.subTest(status=status):
                data["status"] = status
                data["release_date"] = timezone.now()
                form = self.form_class(instance=self.page, data=data)

                self.assertFalse(form.is_valid())
                self.assertFormError(
                    form,
                    "changes_to_release_date",
                    [
                        "If a confirmed calendar entry needs to be rescheduled, "
                        "the 'Changes to release date' field must be filled out."
                    ],
                )

    def test_form_clean__validates_release_date_when_confirmed__happy_path(self):
        """Checks that there are no errors when good data is submitted."""
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["release_date"] = timezone.now()
        data["changes_to_release_date"] = streamfield(
            [("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "The reason"})]
        )
        for status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            with self.subTest(status=status):
                data["status"] = status
                data = nested_form_data(data)
                form = self.form_class(instance=self.page, data=data)

                self.assertTrue(form.is_valid())

    def test_form_clean__set_release_date_text_to_empty_string_for_non_provisional_releases(self):
        """Checks that for non-provisional releases the provisional release date text is set to an empty string."""
        data = self.raw_form_data()
        data["release_date"] = timezone.now()
        data["release_date_text"] = "November 2024"
        data["changes_to_release_date"] = streamfield(
            [("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "The reason"})]
        )

        for status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            with self.subTest(status=status):
                data["status"] = status
                data = nested_form_data(data)
                form = self.form_class(instance=self.page, data=data)

                self.assertTrue(form.is_valid())
                self.assertEqual(form.cleaned_data["release_date_text"], "")

    def test_form_clean__validates_either_next_release_date_or_text(self):
        """Checks that editors can enter either the next release date or the text, not both."""
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["next_release_date"] = timezone.now()
        data["next_release_date_text"] = "November 2024"
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        message = ["Please enter the next release date or the next release text, not both."]
        self.assertFormError(form, "next_release_date", message)
        self.assertFormError(form, "next_release_date_text", message)

    def test_form_clean__validates_next_release_date_is_after_release_date(self):
        """Checks that editors enter a release that that is after the release date."""
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["release_date"] = data["next_release_date"] = timezone.now()
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        message = ["The next release date must be after the release date."]
        self.assertFormError(form, "next_release_date", message)

    def test_form_clean__validates_cannot_cancel_if_in_bundle_ready_to_be_published(self):
        bundle = BundleFactory(release_calendar_page=self.page, approved=True)

        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        data["notice"] = rich_text("")
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)

        self.assertFalse(form.is_valid())

        bundle_url = reverse("bundle:edit", args=[bundle.pk])
        bundle_str = f'<a href="{bundle_url}" target="_blank" title="Manage bundle">{bundle.name}</a>'
        message = (
            f"This release calendar page is linked to bundle '{bundle_str}' which is ready to be published. "
            "Please unschedule the bundle and unlink the release calendar page before making the cancellation."
        )
        self.assertFormError(form, "status", message)

    def test_form_clean__validates_cannot_cancel_if_in_bundle_ready_to_be_published_with_user_without_bundle_access(
        self,
    ):
        bundle = BundleFactory(release_calendar_page=self.page, approved=True)

        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        data["notice"] = rich_text("")
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())

        message = (
            f"This release calendar page is linked to bundle '{bundle.name}' which is ready to be published. "
            "Please unschedule the bundle and unlink the release calendar page before making the cancellation."
        )
        self.assertFormError(form, "status", message)
