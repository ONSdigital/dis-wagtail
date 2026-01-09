import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Locale
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.enums import LOCKED_STATUS_STATUSES, NON_PROVISIONAL_STATUS_CHOICES, ReleaseStatus
from cms.release_calendar.models import ReleaseCalendarPage
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.users.tests.factories import UserFactory


class ReleaseCalendarPageAdminFormTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.publishing_officer = UserFactory(username="publishing_officer")
        officer_group = Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME)
        officer_group.user_set.add(cls.publishing_officer)
        cls.publishing_admin = UserFactory(username="publishing_admin", access_admin=True)
        admin_group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
        admin_group.user_set.add(cls.publishing_admin)

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
        provisional_choices = [choice for choice in ReleaseStatus.choices if choice[0] != ReleaseStatus.PUBLISHED]
        non_provisional_choices = [
            choice for choice in NON_PROVISIONAL_STATUS_CHOICES if choice[0] != ReleaseStatus.PUBLISHED
        ]
        cases = [
            (ReleaseStatus.PROVISIONAL, provisional_choices),
            (ReleaseStatus.CONFIRMED, non_provisional_choices),
            (ReleaseStatus.CANCELLED, non_provisional_choices),
        ]
        for status, choices in cases:
            with self.subTest(status=status, choices=choices):
                self.page.status = status
                form = self.form_class(instance=self.page)

                self.assertEqual(form.fields["status"].choices, choices)

    def test_form_init__status_choices__published(self):
        """Checks that the status choices do not include PUBLISHED."""
        form = self.form_class(instance=self.page)

        self.assertNotIn(ReleaseStatus.PUBLISHED, [choice[0] for choice in form.fields["status"].choices])

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

    def test_form_clean__accepts_published_if_already_published(self):
        """Checks that the form accepts a published status if the page is already published."""
        self.page.status = ReleaseStatus.PUBLISHED
        data = self.form_data
        data["release_date"] = self.page.release_date = datetime.datetime(2025, 1, 2, 3, 4, 0, 0, tzinfo=datetime.UTC)
        data["status"] = ReleaseStatus.PUBLISHED
        form = self.form_class(instance=self.page, data=data)

        # Print any form errors for debugging
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["status"], ReleaseStatus.PUBLISHED)

    def test_form_clean__validates_notice(self):
        """Checks that there is a notice if cancelling."""
        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        self.assertFormError(form, "notice", ["The notice field is required when the release is cancelled"])

    def test_form_clean__validates_release_date_is_mandatory(self):
        """Validates that the release date must be set on all."""
        self.page.release_date = "2032-06-10"
        data = self.form_data
        data["release_date"] = self.page.release_date
        data["notice"] = rich_text("")

        for status in ReleaseStatus:
            if status == ReleaseStatus.PUBLISHED:
                continue
            with self.subTest(status=status):
                self.page.status = data["status"] = status
                form = self.form_class(instance=self.page, data=data)
                self.assertTrue(form.is_valid())

        self.page.release_date = None
        data["release_date"] = None

        for status in ReleaseStatus:
            with self.subTest(status=status):
                self.page.status = data["status"] = status
                form = self.form_class(instance=self.page, data=data)
                self.assertFalse(form.is_valid())

    def test_form_clean__validates_release_date_text_in_english(self):
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
                        [
                            "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY'"
                            " format in English."
                        ],
                    )

    def test_form_clean__validates_release_date_text_in_welsh(self):
        """Validates that the release date text format."""
        data = self.form_data
        welsh_locale, _ = Locale.objects.get_or_create(language_code="cy")

        self.page.locale = welsh_locale
        cases = [
            ("Tachwedd 2024", True),
            ("Tach 2024", False),
            ("Tachwedd 24", False),
            ("Tachwedd 2024 i Rhagfyr 2024", True),
            ("Tachwedd 2024 i anfeidroldeb", False),
            ("Tachwedd 2024 i Rhagfyr 2024 i Ionawr 2025", False),
        ]
        for text, is_valid in cases:
            with self.subTest(text=text, is_valid=is_valid):
                data["release_date_text"] = text
                form = self.form_class(instance=self.page, data=data)

                self.assertEqual(form.is_valid(), is_valid, f"Failed for text: {text}")
                if not is_valid:
                    self.assertFormError(
                        form,
                        "release_date_text",
                        [
                            "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY'"
                            " format in Welsh."
                        ],
                    )

    def test_form_clean__validates_release_date_text_start_end_dates(self):
        """Validates that the release date text with start and end month make sense."""
        data = self.form_data

        data["release_date_text"] = "November 2024 to September 2024"
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        self.assertFormError(form, "release_date_text", ["The end month must be after the start month."])

    def test_form_clean__validates_next_release_date_text_in_english(self):
        """Validates that the next release date text format."""
        data = self.form_data
        data["release_date"] = "2024-01-01T00:00:00Z"
        cases = [
            ("12 November 2024 12:00pm", True),
            ("Nov 2024", False),
            ("November 24", False),
            ("To be confirmed", True),
            ("Lorem ipsum", False),
        ]
        for text, is_valid in cases:
            with self.subTest(text=text, is_valid=is_valid):
                data["next_release_date_text"] = text
                form = self.form_class(instance=self.page, data=data)

                self.assertEqual(form.is_valid(), is_valid)
                if not is_valid:
                    self.assertFormError(
                        form,
                        "next_release_date_text",
                        [
                            'The next release date text must be in the "DD Month YYYY Time" format or say '
                            '"To be confirmed" in English.'
                        ],
                    )

    def test_form_clean__validates_next_release_date_text_in_welsh(self):
        """Validates that the next release date text format."""
        data = self.form_data
        welsh_locale, _ = Locale.objects.get_or_create(language_code="cy")

        self.page.locale = welsh_locale
        data["release_date"] = "2024-01-01T00:00:00Z"
        cases = [
            ("12 Tachwedd 2024 12:00pm", True),
            ("Tach 2024", False),
            ("Tachwedd 24", False),
            ("I’w gadarnhau", True),
            ("Lorem ipsum", False),
        ]
        for text, is_valid in cases:
            with self.subTest(text=text, is_valid=is_valid):
                data["next_release_date_text"] = text
                form = self.form_class(instance=self.page, data=data)

                self.assertEqual(form.is_valid(), is_valid)
                if not is_valid:
                    self.assertFormError(
                        form,
                        "next_release_date_text",
                        [
                            'The next release date text must be in the "DD Month YYYY Time" format or say '
                            '"I’w gadarnhau" in Welsh.'
                        ],
                    )

    def test_form_clean__validates_next_release_date_text_is_after(self):
        data = self.form_data
        data["release_date"] = "2024-01-01T00:00:00Z"
        data["next_release_date_text"] = "12 November 2023 12:00pm"

        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())

        self.assertFormError(
            form,
            "next_release_date_text",
            ["The next release date must be after the release date."],
        )

        data["next_release_date_text"] = "12 November 2024 12:00pm"  # It is later now
        form = self.form_class(instance=self.page, data=data)

        self.assertTrue(form.is_valid())

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
        # Set up the page with a confirmed status and publish it to create a live version
        self.page.status = ReleaseStatus.CONFIRMED
        self.page.release_date = timezone.now()
        self.page.save_revision().publish()

        # Now try to change the release date without adding a change log entry
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["status"] = ReleaseStatus.CONFIRMED
        data["release_date"] = timezone.now() + datetime.timedelta(days=1)  # Different date
        data = nested_form_data(data)
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

    def test_form_clean__validates_change_log_requires_date_change(self):
        """Checks that adding a change log entry requires a different release date."""
        # Set up the page with a confirmed status and publish it to create a live version
        self.page.status = ReleaseStatus.CONFIRMED
        self.page.release_date = timezone.now().replace(second=0)
        self.page.save_revision().publish()

        # Now try to add a change log entry without changing the release date
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["status"] = ReleaseStatus.CONFIRMED
        data["release_date"] = self.page.release_date  # Same date as published
        data["changes_to_release_date"] = streamfield(
            [("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "The reason"})]
        )
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            "changes_to_release_date",
            [
                "You have added a 'Changes to release date' entry, but the release "
                "date is the same as the published version."
            ],
        )

    def test_form_clean__validates_change_log_and_date_change_are_valid(self):
        """Checks that the form is valid when both date and change log are updated together."""
        # Set up the page with a confirmed status and publish it to create a live version
        self.page.status = ReleaseStatus.CONFIRMED
        self.page.release_date = timezone.now()
        self.page.save_revision().publish()

        # Now change both the release date and add a change log entry
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["status"] = ReleaseStatus.CONFIRMED
        data["release_date"] = timezone.now() + datetime.timedelta(days=1)  # Different date
        data["changes_to_release_date"] = streamfield(
            [("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "The reason"})]
        )
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertTrue(form.is_valid())

    def test_form_clean__disallows_multiple_new_change_logs(self):
        """Checks that only one new change log entry can be added per release date change."""
        # Set up the page with a confirmed status and publish it to create a live version
        self.page.status = ReleaseStatus.CONFIRMED
        self.page.release_date = timezone.now()
        self.page.save_revision().publish()

        # Now try to add multiple change log entries with a new release date
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["status"] = ReleaseStatus.CONFIRMED
        data["release_date"] = timezone.now() + datetime.timedelta(days=1)  # Different date
        data["changes_to_release_date"] = streamfield(
            [
                ("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "First reason"}),
                ("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "Second reason"}),
            ]
        )
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            "changes_to_release_date",
            ["Only one 'Changes to release date' entry can be added per release date change."],
        )

    def test_form_clean__validates_notice_cannot_be_removed(self):
        """Checks that the notice cannot be removed from a release calendar page."""
        self.page.status = ReleaseStatus.PROVISIONAL
        self.page.notice = "Lorem ipsum"
        self.page.save_revision().publish()
        data = self.form_data
        data["notice"] = None

        form = self.form_class(instance=self.page, data=data, for_user=self.publishing_officer)

        # The form is valid because the notice field is disabled and defaults to the current notice value.
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["notice"], "Lorem ipsum")

        # Check that always the last published notice is used.
        self.page.notice = "Foo bar"
        self.page.save_revision().publish()
        # Update the value used by the page instance so it differs from the published one.
        self.page.notice = "Hello world"

        form = self.form_class(instance=self.page, data=data, for_user=self.publishing_officer)

        # This scenario triggers the validation, because the notice field is disabled and
        # defaults to the current notice value, not the published one. This makes the form invalid,
        # but the validation function correctly returns the last published notice.
        self.assertFalse(form.is_valid())
        self.assertEqual(form.cleaned_data["notice"], "Foo bar")

        # A publishing admin can clear the notice.
        form = self.form_class(instance=self.page, data=data, for_user=self.publishing_admin)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["notice"], "")

    def test_form_clean__prevents_from_leaving_locked_statuses(self):
        """Checks that the form prevents changing the status from a locked status."""
        data = self.form_data
        data["notice"] = rich_text("")
        for status in LOCKED_STATUS_STATUSES:
            with self.subTest(status=status):
                self.page.status = status
                self.page.save_revision().publish()
                data["status"] = ReleaseStatus.CONFIRMED
                form = self.form_class(instance=self.page, data=data, for_user=self.superuser)
                # Trigger the form validation.
                form.is_valid()
                # Check that the status cannot be changed from a locked status.
                self.assertEqual(form.cleaned_data["status"], status)

    def test_form_clean__allows_leaving_locked_statuses_when_in_draft(self):
        """Checks that the form prevents changing the status from a locked status."""
        data = self.form_data
        self.page.notice = "Lorem ipsum"
        self.page.status = ReleaseStatus.CANCELLED
        self.page.save_revision()
        data["notice"] = rich_text("Lorem ipsum")
        data["status"] = ReleaseStatus.CONFIRMED
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)
        # Trigger the form validation.
        form.is_valid()
        # Check that the status can be changed back to confirmed from a locked status in draft.
        self.assertEqual(form.cleaned_data["status"], ReleaseStatus.CONFIRMED)

        # Now publish cancellation.
        self.page.status = ReleaseStatus.CANCELLED
        self.page.save_revision().publish()

        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)
        form.is_valid()
        # Check that the status cannot be changed from a locked status.
        self.assertEqual(form.cleaned_data["status"], ReleaseStatus.CANCELLED)

    def test_form_clean__validates_release_date_when_confirmed__happy_path(self):
        """Checks that there are no errors when good data is submitted."""
        data = self.raw_form_data()
        data["notice"] = rich_text("")
        data["release_date"] = timezone.now()
        data["changes_to_release_date"] = streamfield(
            [("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "The reason"})]
        )
        data["status"] = ReleaseStatus.CONFIRMED
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertTrue(form.is_valid())

    def test_form_clean__set_release_date_text_to_empty_string_for_non_provisional_releases(self):
        """Checks that for non-provisional releases the provisional release date text is set to an empty string."""
        data = self.raw_form_data()
        data["status"] = ReleaseStatus.PROVISIONAL
        data["release_date"] = timezone.now()
        data["release_date_text"] = "November 2024"
        data["changes_to_release_date"] = streamfield(
            [("date_change_log", {"previous_date": timezone.now(), "reason_for_change": "The reason"})]
        )

        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["release_date_text"], "November 2024")

        data["status"] = ReleaseStatus.CONFIRMED
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
        data["release_date"] = data["next_release_date"] = timezone.now().replace(second=0)
        data = nested_form_data(data)
        form = self.form_class(instance=self.page, data=data)

        self.assertFalse(form.is_valid())
        message = ["The next release date must be after the release date."]
        self.assertFormError(form, "next_release_date", message)

    def test_form_clean__validates_cannot_cancel_if_in_draft_bundle(self):
        """Checks that the form prevents cancellation when the page is in a draft bundle."""
        bundle = BundleFactory(release_calendar_page=self.page)  # Default is DRAFT status

        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        data["notice"] = rich_text("Cancellation notice")
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)

        self.assertFalse(form.is_valid())

        bundle_url = reverse("bundle:edit", args=[bundle.pk])
        bundle_str = f'<a href="{bundle_url}" target="_blank" title="Manage bundle">{bundle.name}</a>'
        message = (
            f"This release calendar page is linked to bundle '{bundle_str}'. "
            "Please unlink the release calendar page from the bundle before cancelling."
        )
        self.assertFormError(form, "status", message)

    def test_form_clean__validates_cannot_cancel_if_in_review_bundle(self):
        """Checks that the form prevents cancellation when the page is in an in-review bundle."""
        bundle = BundleFactory(release_calendar_page=self.page, in_review=True)

        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        data["notice"] = rich_text("Cancellation notice")
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)

        self.assertFalse(form.is_valid())

        bundle_url = reverse("bundle:edit", args=[bundle.pk])
        bundle_str = f'<a href="{bundle_url}" target="_blank" title="Manage bundle">{bundle.name}</a>'
        message = (
            f"This release calendar page is linked to bundle '{bundle_str}'. "
            "Please unlink the release calendar page from the bundle before cancelling."
        )
        self.assertFormError(form, "status", message)

    def test_form_clean__validates_cannot_cancel_if_in_approved_bundle(self):
        """Checks that the form prevents cancellation when the page is in an approved bundle."""
        bundle = BundleFactory(release_calendar_page=self.page, approved=True)

        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        data["notice"] = rich_text("Cancellation notice")
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)

        self.assertFalse(form.is_valid())

        bundle_url = reverse("bundle:edit", args=[bundle.pk])
        bundle_str = f'<a href="{bundle_url}" target="_blank" title="Manage bundle">{bundle.name}</a>'
        message = (
            f"This release calendar page is linked to bundle '{bundle_str}'. "
            "Please unlink the release calendar page from the bundle before cancelling."
        )
        self.assertFormError(form, "status", message)

    def test_form_clean__validates_cannot_cancel_if_in_active_bundle_without_bundle_access(self):
        """Checks that users without bundle access see plain bundle name in error message."""
        bundle = BundleFactory(release_calendar_page=self.page)

        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        data["notice"] = rich_text("Cancellation notice")
        form = self.form_class(instance=self.page, data=data)  # No for_user

        self.assertFalse(form.is_valid())

        message = (
            f"This release calendar page is linked to bundle '{bundle.name}'. "
            "Please unlink the release calendar page from the bundle before cancelling."
        )
        self.assertFormError(form, "status", message)

    def test_form_clean__allows_cancellation_if_bundle_is_published(self):
        """Checks that cancellation is allowed when the bundle has already been published."""
        BundleFactory(release_calendar_page=self.page, published=True)

        data = self.form_data
        data["status"] = ReleaseStatus.CANCELLED
        data["notice"] = rich_text("Cancellation notice")
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)

        # Published bundles are not active, so cancellation should be allowed
        self.assertTrue(form.is_valid())

    def test_form_clean__allows_other_status_changes_when_in_active_bundle(self):
        """Checks that non-cancelled status changes are allowed when in an active bundle."""
        BundleFactory(release_calendar_page=self.page)  # Draft bundle

        data = self.form_data
        data["status"] = ReleaseStatus.CONFIRMED  # Change from PROVISIONAL to CONFIRMED
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)

        self.assertTrue(form.is_valid())

    def test_form_clean__allows_editing_other_fields_when_in_active_bundle(self):
        """Checks that editing non-status fields is allowed when in an active bundle."""
        BundleFactory(release_calendar_page=self.page)  # Draft bundle

        data = self.form_data
        data["title"] = "Updated Title"
        data["summary"] = rich_text("Updated summary content")
        form = self.form_class(instance=self.page, data=data, for_user=self.superuser)

        self.assertTrue(form.is_valid())

    def test_form_clean__sets_release_date_seconds_to_zero(
        self,
    ):
        form = self.form_class(instance=self.page, data=self.form_data)

        self.assertTrue(form.is_valid())

        self.assertEqual(form.cleaned_data["release_date"].second, 0)

    def test_changes_to_release_date_is_removed_from_the_form_on_page_creation(self):
        """Check that the changes_to_release_date field is not present when creating a new page."""
        unsaved_page = ReleaseCalendarPageFactory.build()
        form = self.form_class(instance=unsaved_page, data=self.form_data)

        self.assertTrue(form.is_valid())
        self.assertNotIn("changes_to_release_date", form.fields)

    def test_changes_to_release_date_is_present_when_editing_an_existing_page(self):
        """Check that the changes_to_release_date field is present when editing an existing page."""
        form = self.form_class(instance=self.page, data=self.form_data)

        self.assertTrue(form.is_valid())
        self.assertIn("changes_to_release_date", form.fields)
