from django.test import TestCase
from django.utils import timezone
from wagtail.test.utils.form_data import inline_formset, nested_form_data, rich_text, streamfield

from cms.release_calendar.enums import NON_PROVISIONAL_STATUS_CHOICES, ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarPage
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


class ReleaseCalendarPageAdminFormTestCase(TestCase):
    """ReleaseCalendarPageForm tests."""

    def setUp(self):
        self.page = ReleaseCalendarPageFactory()
        self.form_class = ReleaseCalendarPage.get_edit_handler().get_form_class()  # pylint: disable=no-member
        self.form_data = nested_form_data(self.raw_form_data())

    def raw_form_data(self, page=None):
        """Returns raw form data."""
        the_page = page or self.page
        return {
            # required fields
            "title": the_page.title,
            "slug": the_page.slug,
            "summary": rich_text(the_page.summary),
            "content": streamfield([]),
            "changes_to_release_date": streamfield([]),
            "pre_release_access": streamfield([]),
            # our values
            "status": ReleaseStatus.PROVISIONAL,
            "notice": '{"entityMap": {},"blocks": []}',  # an empty rich text
            "related_links": inline_formset([]),
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
        self.assertListEqual(form.errors["notice"], ["The notice field is required when the release is cancelled"])

    def test_form_clean__validates_release_date_when_confirmed(self):
        """Validates that the release date must be set if the release is confirmed."""
        data = self.form_data

        cases = [
            (ReleaseStatus.PROVISIONAL, True),
            (ReleaseStatus.CANCELLED, True),
            (ReleaseStatus.CONFIRMED, False),
            (ReleaseStatus.PUBLISHED, False),
        ]
        for status, is_valid in cases:
            with self.subTest(status=status, is_valid=is_valid):
                data["status"] = status
                data["notice"] = rich_text("")
                form = self.form_class(instance=self.page, data=data)

                self.assertEqual(form.is_valid(), is_valid)
                if not is_valid:
                    self.assertListEqual(
                        form.errors["release_date"],
                        ["The release date field is required when the release is confirmed"],
                    )

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
                    self.assertListEqual(
                        form.errors["release_date_text"],
                        ["The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format."],
                    )

    def test_form_clean__validates_release_date_text_start_end_dates(self):
        """Validates that the release date text with start and end month make sense."""
        data = self.form_data
        data["release_date_text"] = "November 2024 to September 2024"
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        self.assertListEqual(form.errors["release_date_text"], ["The end month must be after the start month."])

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
        self.page.release_date = timezone.now()
        data = self.form_data
        data["notice"] = rich_text("")

        for status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            with self.subTest(status=status):
                data["status"] = status
                data["release_date"] = timezone.now()
                form = self.form_class(instance=self.page, data=data)

                self.assertFalse(form.is_valid())
                self.assertListEqual(
                    form.errors["changes_to_release_date"],
                    [
                        "If a confirmed calendar entry needs to be rescheduled, "
                        "the 'Changes to release date' field must be filled out."
                    ],
                )

    def test_form_clean__validates_changes_to_release_date_cannot_be_removed(self):
        """Tests that one cannot remove changes_to_release_date data."""
        self.page.changes_to_release_date = [
            {"type": "date_change_log", "value": {"previous_date": timezone.now(), "reason_for_change": "The reason"}}
        ]
        data = self.raw_form_data(page=self.page)
        data["notice"] = rich_text("")
        data["release_date"] = timezone.now()
        data["changes_to_release_date"] = streamfield([])

        for status in [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED]:
            with self.subTest(status=status):
                data["status"] = status

                data = nested_form_data(data)
                form = self.form_class(instance=self.page, data=data)

                self.assertFalse(form.is_valid())
                self.assertListEqual(
                    form.errors["changes_to_release_date"],
                    ["You cannot remove entries from the 'Changes to release date'."],
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

    def test_form_clean__validates_either_release_date_or_text(self):
        """Checks that editors can enter either the release date or the text, not both."""
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["release_date"] = timezone.now()
        data["release_date_text"] = "November 2024"
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        message = ["Please enter the release date or the release date text, not both."]
        self.assertListEqual(form.errors["release_date"], message)
        self.assertListEqual(form.errors["release_date_text"], message)

    def test_form_clean__validates_either_next_release_date_or_text(self):
        """Checks that editors can enter either the next release date or the text, not both."""
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["next_release_date"] = timezone.now()
        data["next_release_text"] = "November 2024"
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        message = ["Please enter the next release date or the next release text, not both."]
        self.assertListEqual(form.errors["next_release_date"], message)
        self.assertListEqual(form.errors["next_release_text"], message)
