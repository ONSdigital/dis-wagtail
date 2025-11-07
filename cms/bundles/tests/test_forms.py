from datetime import timedelta
from typing import Any

from django import forms
from django.test import TestCase
from django.utils import timezone
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.bundles.admin_forms import AddToBundleForm
from cms.bundles.enums import ACTIVE_BUNDLE_STATUS_CHOICES, BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory, BundlePageFactory, BundleTeamFactory
from cms.bundles.viewsets.bundle_chooser import BundleChooserWidget
from cms.datasets.tests.factories import DatasetFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_to_publish


class AddToBundleFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="First Bundle")
        cls.non_editable_bundle = BundleFactory(approved=True)
        cls.page = StatisticalArticlePageFactory(title="The Statistical Article")

    def test_form_init(self):
        """Checks the form gets a bundle form field on init."""
        form = AddToBundleForm(page_to_add=self.page)
        self.assertIn("bundle", form.fields)
        self.assertIsInstance(form.fields["bundle"].widget, BundleChooserWidget)
        self.assertQuerySetEqual(
            form.fields["bundle"].queryset,
            Bundle.objects.filter(pk=self.bundle.pk),
        )

    def test_form_clean__validates_page_not_in_bundle(self):
        """Checks that we cannot add the page to a new bundle if already in an active one."""
        BundlePageFactory(parent=self.bundle, page=self.page)
        form = AddToBundleForm(page_to_add=self.page, data={"bundle": self.bundle.pk})

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form, "bundle", [f"Page '{self.page.get_admin_display_title()}' is already in bundle 'First Bundle'"]
        )

    def test_form_clean__validates_page_is_bundleable(self):
        """Checks the given page inherits from BundlePageMixin."""
        form = AddToBundleForm(page_to_add=ArticleSeriesPageFactory(), data={"bundle": self.bundle.pk})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, ["Pages of this type cannot be added."])


class BundleAdminFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="First Bundle")
        cls.form_class = get_edit_handler(Bundle).get_form_class()

        cls.page = StatisticalArticlePageFactory(title="The Statistical Article")
        cls.page_ready_to_publish = StatisticalArticlePageFactory(title="Statistically Ready")

        cls.approver = UserFactory()
        mark_page_as_ready_to_publish(cls.page_ready_to_publish, cls.approver)

    def setUp(self):
        self.form_data = nested_form_data(self.raw_form_data())

    def raw_form_data(self) -> dict[str, Any]:
        """Returns raw form data."""
        return {
            "name": "First Bundle",
            "status": BundleStatus.IN_REVIEW,
            "bundled_pages": inline_formset([{"page": self.page.id}]),
            "teams": inline_formset([]),
            "bundled_datasets": inline_formset([]),
        }

    def _setup_bundle(self, ready_to_publish: bool = True) -> dict[str, Any]:
        """Sets up the bundle and returns raw form data."""
        page = StatisticalArticlePageFactory(title="A Page")
        if ready_to_publish:
            mark_page_as_ready_to_publish(page, self.approver)

        dataset = DatasetFactory(id=123)
        team = TeamFactory(id=123)

        bundled_page = BundlePageFactory(parent=self.bundle, page=page)
        bundled_dataset = BundleDatasetFactory(parent=self.bundle, dataset=dataset)
        bundled_team = BundleTeamFactory(parent=self.bundle, team=team)

        return {
            "name": self.bundle.name,
            "status": self.bundle.status,
            "bundled_pages": inline_formset([{"id": bundled_page.id, "page": page.id, "ORDER": "1"}], initial=1),
            "bundled_datasets": inline_formset(
                [{"id": bundled_dataset.id, "dataset": dataset.id, "ORDER": "1"}], initial=1
            ),
            "teams": inline_formset([{"id": bundled_team.id, "team": team.id, "ORDER": "1"}], initial=1),
        }

    def test_form_init__status_choices(self):
        """Checks status choices variation."""
        cases = [
            (BundleStatus.DRAFT, ACTIVE_BUNDLE_STATUS_CHOICES),
            (BundleStatus.IN_REVIEW, ACTIVE_BUNDLE_STATUS_CHOICES),
            (BundleStatus.APPROVED, BundleStatus.choices),
            (BundleStatus.PUBLISHED, BundleStatus.choices),
        ]
        for status, choices in cases:
            with self.subTest(status=status, choices=choices):
                self.bundle.status = status
                form = self.form_class(instance=self.bundle)
                self.assertEqual(form.fields["status"].choices, choices)

    def test_form_init__approved_by_at_are_disabled(self):
        """Checks that approved_at and approved_by are disabled. They are programmatically set."""
        form = self.form_class(instance=self.bundle)
        self.assertTrue(form.fields["approved_at"].disabled)
        self.assertTrue(form.fields["approved_by"].disabled)

        self.assertIsInstance(form.fields["approved_by"].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields["approved_at"].widget, forms.HiddenInput)

    def test_form_init__fields_disabled_if_status_is_approved(self):
        """Checks that all but the status field are disabled once approved to prevent further editing."""
        self.bundle.status = BundleStatus.APPROVED
        form = self.form_class(instance=self.bundle)
        fields = dict.fromkeys(form.fields, True)
        fields["status"] = False

        for field, expected in fields.items():
            with self.subTest(field=field, expected=expected):
                self.assertEqual(form.fields[field].disabled, expected)

    def test_clean__removes_deleted_page_references(self):
        """Checks that we clean up references to pages that may have been deleted since being added to the bundle."""
        raw_data = self.raw_form_data()
        raw_data["bundled_pages"] = inline_formset([{"page": ""}])
        data = nested_form_data(raw_data)

        form = self.form_class(instance=self.bundle, data=data)

        self.assertTrue(form.is_valid())
        formset = form.formsets["bundled_pages"]
        self.assertTrue(formset.forms[0].cleaned_data["DELETE"])

    def test_clean__validates_added_page_not_in_another_bundle(self):
        """Should validate that the page is not in the active bundle."""
        another_bundle = BundleFactory(name="Another Bundle")
        BundlePageFactory(parent=another_bundle, page=self.page)

        raw_data = self.raw_form_data()
        raw_data["bundled_pages"] = inline_formset([{"page": self.page.id}])

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, ["'The Statistical Article' is already in an active bundle (Another Bundle)"])

    def test_clean__validates_release_calendar_page_not_already_used(self):
        """Should validate that the page is not in the active bundle."""
        nowish = timezone.now() + timedelta(minutes=5)
        release_calendar_page = ReleaseCalendarPageFactory(release_date=nowish, title="Release Calendar Page")
        raw_data = self.raw_form_data()
        raw_data["release_calendar_page"] = release_calendar_page.id
        raw_data["bundled_pages"] = inline_formset([{"page": release_calendar_page.id}])

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))
        self.assertFalse(form.is_valid())
        self.assertFormError(
            form, None, ["'Release Calendar Page' is already set as the Release Calendar page for this bundle."]
        )

    def test_clean__sets_approved_by_and_approved_at_when_no_other_changes(self):
        # Given
        raw_data = self._setup_bundle()

        # When
        raw_data["status"] = BundleStatus.APPROVED

        # Then
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["approved_by"], self.approver)
        self.assertIsNotNone(form.cleaned_data["approved_at"])

    def test_clean__validates_page_must_be_ready_for_review(self):
        data = self._setup_bundle(ready_to_publish=False)
        data["status"] = BundleStatus.APPROVED
        form = self.form_class(instance=self.bundle, data=nested_form_data(data), for_user=self.bundle.created_by)

        self.assertFalse(form.is_valid())

        self.assertFormError(form, None, "Cannot approve the bundle with 1 page not ready to be published.")
        self.assertFormSetError(form.formsets["bundled_pages"], 0, "page", "This page is not ready to be published")

        self.assertIsNone(form.cleaned_data["approved_by"])
        self.assertIsNone(form.cleaned_data["approved_at"])

    def test_clean__validates_release_calendar_page_or_publication_date(self):
        nowish = timezone.now() + timedelta(minutes=5)
        release_calendar_page = ReleaseCalendarPageFactory(release_date=nowish)
        data = self.form_data
        data["release_calendar_page"] = release_calendar_page.id
        data["publication_date"] = nowish

        form = self.form_class(data=data)

        self.assertFalse(form.is_valid())

        error = "You must choose either a Release Calendar page or a Publication date, not both."
        self.assertFormError(form, "release_calendar_page", [error])
        self.assertFormError(form, "publication_date", [error])

    def test_clean__removes_duplicate_pages(self):
        self.assertEqual(self.bundle.bundled_pages.count(), 0)

        raw_data = self.raw_form_data()
        raw_data["bundled_pages"] = inline_formset([{"page": self.page.id}, {"page": self.page.id}])

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid())

        form.save()

        self.assertEqual(self.bundle.bundled_pages.count(), 1)

    def test_clean__removes_duplicate_datasets(self):
        dataset = DatasetFactory(id=123)
        self.assertEqual(self.bundle.bundled_datasets.count(), 0)

        raw_data = self.raw_form_data()
        raw_data["bundled_datasets"] = inline_formset([{"dataset": dataset.pk}, {"dataset": dataset.pk}])

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid())

        form.save()

        self.assertEqual(self.bundle.bundled_datasets.count(), 1)

    def test_clean__removes_duplicate_teams(self):
        team = TeamFactory()
        self.assertEqual(self.bundle.teams.count(), 0)

        raw_data = self.raw_form_data()
        raw_data["teams"] = inline_formset([{"team": team.pk}, {"team": team.pk}])

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid())

        form.save()

        self.assertEqual(self.bundle.teams.count(), 1)

    def test_clean_validates_release_calendar_page_date_is_future(self):
        release_calendar_page = ReleaseCalendarPageFactory(release_date=timezone.now() - timedelta(hours=2))
        data = self.form_data

        data["release_calendar_page"] = release_calendar_page.id
        data["status"] = BundleStatus.DRAFT
        form = self.form_class(instance=self.bundle, data=data)
        self.assertFalse(form.is_valid())

        self.assertFormError(
            form, "release_calendar_page", ["The release date on the release calendar page cannot be in the past."]
        )

    def test_clean_validates_release_date_is_in_future(self):
        data = self.form_data
        data["publication_date"] = timezone.now() - timedelta(hours=2)
        data["status"] = BundleStatus.DRAFT
        form = self.form_class(instance=self.bundle, data=data)
        self.assertFalse(form.is_valid())

        self.assertFormError(form, "publication_date", ["The release date cannot be in the past."])

    def test_clean_validates_the_bundle_has_content(self):
        raw_data = self.raw_form_data()
        raw_data["bundled_pages"] = inline_formset([])
        raw_data["status"] = BundleStatus.APPROVED

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))

        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, "Cannot approve the bundle without any pages or datasets")

        # add a dataset
        DatasetFactory(id=123)
        raw_data = self.raw_form_data()
        raw_data["bundled_datasets"] = inline_formset([{"dataset": 123}])
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))
        self.assertTrue(form.is_valid())

    def test_clean_validates_the_bundle_has_datasets(self):
        dataset = DatasetFactory(id=123)
        raw_data = self.raw_form_data()
        raw_data["bundled_datasets"] = inline_formset([{"dataset": dataset.pk}])
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))

        self.assertTrue(form.is_valid())

    def test_clean_validates_the_bundle_has_valid_datasets(self):
        raw_data = self.raw_form_data()
        raw_data["bundled_datasets"] = inline_formset([{"dataset": 9999}])  # Invalid dataset ID
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data))

        self.assertFalse(form.is_valid())

    def test_clean_sets_publication_date_seconds_to_zero(self):
        form = self.form_class(
            instance=self.bundle,
            data=nested_form_data(self.raw_form_data() | {"publication_date": timezone.now() + timedelta(days=1)}),
        )

        self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(form.cleaned_data["publication_date"].second, 0)

    def test_clean__preserves_past_release_calendar_page_when_unscheduling(self):
        release_calendar_page = ReleaseCalendarPageFactory(release_date=timezone.now() - timedelta(minutes=5))
        self.bundle.release_calendar_page = release_calendar_page
        self.bundle.status = BundleStatus.APPROVED

        self.bundle.save(update_fields=["status", "release_calendar_page"])

        data = self.form_data
        # Not adding the release_calendar_page field in the data as is disabled when editing a bundle in
        # "Ready to publish", which means no data is sent
        data["status"] = BundleStatus.DRAFT.value
        form = self.form_class(instance=self.bundle, data=data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["release_calendar_page"], self.bundle.release_calendar_page)

    def test_clean__preserves_past_publication_when_unscheduling(self):
        self.bundle.publication_date = timezone.now() - timedelta(minutes=5)
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status", "publication_date"])

        data = self.form_data
        # Not adding the publication_date field in the data as is disabled when editing a bundle in
        # "Ready to publish", which means no data is sent
        data["status"] = BundleStatus.DRAFT.value
        form = self.form_class(instance=self.bundle, data=data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["publication_date"], self.bundle.publication_date)

    def test_clean__rejects_other_field_changes_when_approving(self):
        """Approving while changing another field should raise a validation error."""
        # Given
        raw_data = self._setup_bundle()

        # When
        raw_data["name"] = "Renamed Bundle"  # disallowed concurrent change
        raw_data["publication_date"] = timezone.now() + timedelta(days=2)  # disallowed concurrent change
        raw_data["status"] = BundleStatus.APPROVED

        # Then
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        for field in ["name", "publication_date"]:
            self.assertFormError(
                form,
                field,
                "You cannot make changes to this field when approving a bundle. "
                "Please save your changes first, then Approve the bundle in a separate step.",
            )
        self.assertEqual(form.cleaned_data.get("status"), self.bundle.status)
        self.assertIsNone(form.cleaned_data.get("approved_by"))
        self.assertIsNone(form.cleaned_data.get("approved_at"))

    def test_clean__rejects_formset_addition_when_approving(self):
        """Approving while adding to a formset in the same submit should raise a validation error."""
        # Given
        raw_data = self._setup_bundle()
        raw_data["status"] = BundleStatus.APPROVED

        cases = [
            # formset_name, field_name, extra_instance
            ("bundled_pages", "page", StatisticalArticlePageFactory(title="New Page")),
            ("bundled_datasets", "dataset", DatasetFactory(id=456)),
            ("teams", "team", TeamFactory(id=456)),
        ]

        for formset_name, field_name, extra_instance in cases:
            with self.subTest(formset=formset_name):
                existing_field = getattr(self.bundle, formset_name).first()
                existing_field_id = getattr(existing_field, field_name).id

                # When
                # Add a new item to the formset alongside the existing one
                raw_data[formset_name] = inline_formset(
                    [{field_name: existing_field_id}, {field_name: extra_instance.id}]
                )

                # Then
                form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

                self.assertFalse(form.is_valid())
                self.assertFormError(
                    form,
                    None,
                    "You cannot make changes to pages, datasets, or teams when approving a bundle. "
                    "Please save your changes first, then Approve the bundle in a separate step.",
                )
                self.assertEqual(form.cleaned_data.get("status"), self.bundle.status)
                self.assertIsNone(form.cleaned_data.get("approved_by"))
                self.assertIsNone(form.cleaned_data.get("approved_at"))

    def test_clean__rejects_formset_deletion_when_approving(self):
        """Approving while deleting a formset item in the same submit should raise a validation error."""
        # Given
        raw_data = self._setup_bundle()
        raw_data["status"] = BundleStatus.APPROVED

        cases = [
            # formset_name, field_name
            ("bundled_pages", "page"),
            ("bundled_datasets", "dataset"),
            ("teams", "team"),
        ]

        for formset_name, field_name in cases:
            with self.subTest(formset=formset_name):
                existing_field = getattr(self.bundle, formset_name).first()
                existing_field_id = getattr(existing_field, field_name).id

                # When
                # Mark the existing item for deletion in the formset
                raw_data[formset_name] = inline_formset([{field_name: existing_field_id, "DELETE": True}])

                # Then
                form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

                self.assertFalse(form.is_valid())
                self.assertFormError(
                    form,
                    None,
                    "You cannot make changes to pages, datasets, or teams when approving a bundle. "
                    "Please save your changes first, then Approve the bundle in a separate step.",
                )
                self.assertEqual(form.cleaned_data.get("status"), self.bundle.status)
                self.assertIsNone(form.cleaned_data.get("approved_by"))
                self.assertIsNone(form.cleaned_data.get("approved_at"))

    def test_clean__approval_error_preserves_non_status_fields(self):
        """When approval raises ValidationError, keep other fields as submitted and reset status to original."""
        # Given
        raw_data = self._setup_bundle()
        raw_data["status"] = BundleStatus.APPROVED

        # When
        # Change a disallowed field alongside approving to trigger the guard
        submitted_name = "Renamed Bundle"
        publication_date = timezone.now() + timedelta(days=2)
        raw_data["name"] = submitted_name
        raw_data["publication_date"] = publication_date

        # Then
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())

        # Status is reset back to the original instance value
        self.assertEqual(form.cleaned_data.get("status"), self.bundle.status)

        # Other submitted fields persist
        self.assertEqual(form.data.get("name"), submitted_name)
        self.assertEqual(form.data.get("publication_date"), publication_date)

        # Assert fields other than status are not disabled. Approval disables form fields to prevent changes.
        self.assertFalse(form.fields["name"].disabled)
        self.assertFalse(form.fields["publication_date"].disabled)
        self.assertFalse(form.fields["release_calendar_page"].disabled)

    # test to validate approval validation is run before other clean logic
    def test_clean__approval_validated_before_other_logic(self):
        """When approving, approval validation should run before other clean logic like field validation."""
        # Given
        raw_data = self._setup_bundle()

        # Add publication date in the past to trigger validation error
        raw_data["publication_date"] = timezone.now() - timedelta(days=2)

        for status in [BundleStatus.DRAFT, BundleStatus.APPROVED]:
            with self.subTest(status=status):
                raw_data["status"] = status

                form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

                self.assertFalse(form.is_valid())
                if status == BundleStatus.APPROVED:
                    error_msg = (
                        "You cannot make changes to this field when approving a bundle. "
                        "Please save your changes first, then Approve the bundle in a separate step."
                    )
                else:
                    error_msg = "The release date cannot be in the past."

                self.assertFormError(form, "publication_date", [error_msg])
