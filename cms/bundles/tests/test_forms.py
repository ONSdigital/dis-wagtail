from datetime import timedelta
from typing import Any
from unittest.mock import patch

from django import forms
from django.test import TestCase, override_settings
from django.utils import timezone
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.bundles.admin_forms import AddToBundleForm
from cms.bundles.clients.api import BundleAPIClientError
from cms.bundles.enums import ACTIVE_BUNDLE_STATUS_CHOICES, BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
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

    def test_clean__sets_approved_by_and_approved_at(self):
        raw_data = self.raw_form_data()
        raw_data["bundled_pages"] = inline_formset([{"page": self.page_ready_to_publish.id}])
        raw_data["status"] = BundleStatus.APPROVED
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["approved_by"], self.approver)

    def test_clean__validates_page_must_be_ready_for_review(self):
        data = self.form_data
        data["status"] = BundleStatus.APPROVED
        form = self.form_class(instance=self.bundle, data=data, for_user=self.bundle.created_by)

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
        data["status"] = BundleStatus.APPROVED
        form = self.form_class(instance=self.bundle, data=data)
        self.assertFalse(form.is_valid())

        self.assertFormError(
            form, "release_calendar_page", ["The release date on the release calendar page cannot be in the past."]
        )

    def test_clean_validates_release_date_is_in_future(self):
        data = self.form_data
        data["publication_date"] = timezone.now() - timedelta(hours=2)
        data["status"] = BundleStatus.APPROVED
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


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
class BundleDatasetValidationTestCase(TestCase):
    """Test cases for dataset validation in the BundleAdminForm."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Test Bundle")
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def raw_form_data_with_dataset(self, dataset_id: int) -> dict[str, Any]:
        """Returns raw form data with a dataset."""
        return {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset_id}]),
            "teams": inline_formset([]),
        }

    def test_dataset_validation_approved_dataset_passes(self):
        """Test that approved datasets pass validation."""
        dataset = DatasetFactory(id=123)
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.return_value = {
            "contents": [
                {
                    "id": "content-1",
                    "state": "APPROVED",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                    },
                }
            ]
        }

        raw_data = self.raw_form_data_with_dataset(dataset.id)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_called_once_with("test-bundle-123")

    def test_dataset_validation_unapproved_dataset_fails(self):
        """Test that unapproved datasets fail validation."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.return_value = {
            "contents": [
                {
                    "id": "content-1",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                    },
                }
            ]
        }

        raw_data = self.raw_form_data_with_dataset(dataset.id)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            ["Cannot approve the bundle with 1 dataset not ready to be published: Test Dataset (state: DRAFT)"],
        )

    def test_dataset_validation_multiple_datasets_mixed_statuses(self):
        """Test validation with multiple datasets having different statuses."""
        dataset1 = DatasetFactory(id=123, title="Approved Dataset")
        dataset2 = DatasetFactory(id=124, title="Draft Dataset")
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.return_value = {
            "contents": [
                {
                    "id": "content-1",
                    "state": "APPROVED",
                    "metadata": {
                        "dataset_id": dataset1.namespace,
                        "edition_id": dataset1.edition,
                        "version_id": dataset1.version,
                    },
                },
                {
                    "id": "content-2",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset2.namespace,
                        "edition_id": dataset2.edition,
                        "version_id": dataset2.version,
                    },
                },
            ]
        }

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset1.id}, {"dataset": dataset2.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            ["Cannot approve the bundle with 1 dataset not ready to be published: Draft Dataset (state: DRAFT)"],
        )

    def test_dataset_validation_multiple_datasets_not_ready(self):
        """Test that multiple datasets not ready shows proper pluralization."""
        dataset1 = DatasetFactory(id=123, title="Draft Dataset 1")
        dataset2 = DatasetFactory(id=124, title="Draft Dataset 2")
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.return_value = {
            "contents": [
                {
                    "id": "content-1",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset1.namespace,
                        "edition_id": dataset1.edition,
                        "version_id": dataset1.version,
                    },
                },
                {
                    "id": "content-2",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset2.namespace,
                        "edition_id": dataset2.edition,
                        "version_id": dataset2.version,
                    },
                },
            ]
        }

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset1.id}, {"dataset": dataset2.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            [
                "Cannot approve the bundle with 2 datasets not ready to be published: "
                "Draft Dataset 1 (state: DRAFT), Draft Dataset 2 (state: DRAFT)"
            ],
        )

    def test_dataset_validation_api_error_fails_gracefully(self):
        """Test that API errors are handled gracefully."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.side_effect = BundleAPIClientError("API Error")

        raw_data = self.raw_form_data_with_dataset(dataset.id)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())
        self.assertFormError(
            form,
            None,
            ["Cannot approve the bundle with 1 dataset not ready to be published: Bundle content validation failed"],
        )

    def test_dataset_validation_only_runs_when_approving(self):
        """Test that dataset validation only runs when changing status to APPROVED."""
        dataset = DatasetFactory(id=123)
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.return_value = {
            "contents": [
                {
                    "id": "content-1",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": dataset.namespace,
                        "edition_id": dataset.edition,
                        "version_id": dataset.version,
                    },
                }
            ]
        }

        raw_data = self.raw_form_data_with_dataset(dataset.id)
        raw_data["status"] = BundleStatus.IN_REVIEW  # Not approving

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_not_called()

    def test_dataset_validation_skipped_when_no_datasets(self):
        """Test that dataset validation is skipped when there are no datasets."""
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertFalse(form.is_valid())  # Should fail because no pages or datasets
        self.mock_client.get_bundle_contents.assert_not_called()

    def test_dataset_validation_skipped_when_no_bundle_api_id(self):
        """Test that dataset validation is skipped when bundle has no API ID."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        # Bundle doesn't have bundle_api_id set
        self.assertIsNone(self.bundle.bundle_api_id)

        raw_data = self.raw_form_data_with_dataset(dataset.id)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_not_called()

    def test_dataset_validation_empty_contents_array(self):
        """Test validation handles empty contents array from API."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.return_value = {"contents": []}

        raw_data = self.raw_form_data_with_dataset(dataset.id)
        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        self.mock_client.get_bundle_contents.assert_called_once_with("test-bundle-123")

    def test_dataset_validation_handles_deleted_datasets(self):
        """Test that validation handles datasets marked for deletion."""
        dataset1 = DatasetFactory(id=123, title="Approved Dataset")
        dataset2 = DatasetFactory(id=124, title="Deleted Dataset")
        self.bundle.bundle_api_id = "test-bundle-123"
        self.bundle.save()

        self.mock_client.get_bundle_contents.return_value = {
            "contents": [
                {
                    "id": "content-1",
                    "state": "APPROVED",
                    "metadata": {
                        "dataset_id": dataset1.namespace,
                        "edition_id": dataset1.edition,
                        "version_id": dataset1.version,
                    },
                }
            ]
        }

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset1.id}, {"dataset": dataset2.id, "DELETE": True}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        # Should check bundle contents once
        self.mock_client.get_bundle_contents.assert_called_once_with("test-bundle-123")


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
class BundleDatasetValidationDisabledTestCase(TestCase):
    """Test cases for dataset validation when API is disabled."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Test Bundle")
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def test_dataset_validation_skipped_when_api_disabled(self):
        """Test that dataset validation is skipped when DIS_DATASETS_BUNDLE_API_ENABLED is False."""
        dataset = DatasetFactory(id=123, title="Test Dataset")

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.APPROVED,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=self.bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        # API client should not be called when disabled
        self.mock_client.get_bundle_contents.assert_not_called()


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
class BundleFormSaveTestCase(TestCase):
    """Test cases for the BundleAdminForm save method."""

    @classmethod
    def setUpTestData(cls):
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def test_save_new_bundle_without_datasets_does_not_call_api(self):
        """Test that saving a new bundle without datasets doesn't call the API."""
        self.mock_client.create_bundle.return_value = {"id": "api-bundle-123"}

        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should not be called for bundles without datasets
        self.mock_client.create_bundle.assert_not_called()
        self.assertIsNone(bundle.bundle_api_id)

    def test_save_new_bundle_with_datasets_calls_api(self):
        """Test that saving a new bundle with datasets calls the API."""
        self.mock_client.create_bundle.return_value = {"id": "api-bundle-123"}

        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called for bundles with datasets
        self.mock_client.create_bundle.assert_called_once()
        call_args = self.mock_client.create_bundle.call_args[0][0]
        self.assertEqual(call_args["title"], "Test Bundle")
        self.assertEqual(call_args["bundle_type"], "MANUAL")
        self.assertEqual(call_args["state"], "DRAFT")
        self.assertEqual(call_args["managed_by"], "WAGTAIL")

        # Content should be added separately
        self.mock_client.add_content_to_bundle.assert_called_once()
        content_call_args = self.mock_client.add_content_to_bundle.call_args[0]
        self.assertEqual(content_call_args[0], "api-bundle-123")  # bundle_id
        content_item = content_call_args[1]
        self.assertEqual(content_item["content_type"], "DATASET")
        self.assertEqual(content_item["metadata"]["dataset_id"], dataset.namespace)

        # Bundle should have the API ID set
        self.assertEqual(bundle.bundle_api_id, "api-bundle-123")

    def test_save_existing_bundle_uses_standard_behavior(self):
        """Test that saving an existing bundle uses standard Django form behavior."""
        existing_bundle = BundleFactory(name="Existing Bundle")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should not be called for existing bundles in form save
        self.mock_client.create_bundle.assert_not_called()
        self.assertEqual(bundle.name, "Updated Bundle")

    def test_save_new_bundle_with_datasets_api_error_does_not_break_save(self):
        """Test that API errors during bundle creation don't prevent saving."""
        self.mock_client.create_bundle.side_effect = BundleAPIClientError("API Error")

        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        # This should not raise an exception
        bundle = form.save()

        # The bundle should still be saved
        self.assertTrue(bundle.pk)
        self.assertEqual(bundle.name, "Test Bundle")
        self.assertIsNone(bundle.bundle_api_id)

    def test_save_new_bundle_with_datasets_no_api_id_returned(self):
        """Test handling when API doesn't return an ID."""
        self.mock_client.create_bundle.return_value = {"message": "Created but no ID"}

        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called but bundle should not have API ID
        self.mock_client.create_bundle.assert_called_once()
        self.assertIsNone(bundle.bundle_api_id)

    def test_save_existing_bundle_with_first_dataset_calls_api(self):
        """Test that editing an existing bundle to add its first dataset calls the API."""
        self.mock_client.create_bundle.return_value = {"id": "api-bundle-456"}

        # Create an existing bundle without datasets
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_id=None)
        dataset = DatasetFactory(id=123, title="Test Dataset")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should be called when adding first dataset to existing bundle
        self.mock_client.create_bundle.assert_called_once()
        call_args = self.mock_client.create_bundle.call_args[0][0]
        self.assertEqual(call_args["title"], "Updated Bundle")
        self.assertEqual(call_args["bundle_type"], "MANUAL")
        self.assertEqual(call_args["state"], "DRAFT")
        self.assertEqual(call_args["managed_by"], "WAGTAIL")

        # Content should be added separately
        self.mock_client.add_content_to_bundle.assert_called_once()
        content_call_args = self.mock_client.add_content_to_bundle.call_args[0]
        self.assertEqual(content_call_args[0], "api-bundle-456")  # bundle_id
        content_item = content_call_args[1]
        self.assertEqual(content_item["content_type"], "DATASET")
        self.assertEqual(content_item["metadata"]["dataset_id"], dataset.namespace)

        # Bundle should have the API ID set
        self.assertEqual(bundle.bundle_api_id, "api-bundle-456")

    def test_save_existing_bundle_with_existing_api_id_does_not_call_api(self):
        """Test that editing an existing bundle that already has an API ID doesn't call create_bundle."""
        # Create an existing bundle with API ID
        existing_bundle = BundleFactory(name="Existing Bundle", bundle_api_id="existing-api-id")
        dataset = DatasetFactory(id=123, title="Test Dataset")

        raw_data = {
            "name": "Updated Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(instance=existing_bundle, data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should NOT be called for bundles that already have an API ID
        self.mock_client.create_bundle.assert_not_called()
        self.assertEqual(bundle.bundle_api_id, "existing-api-id")


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
class BundleFormSaveDisabledTestCase(TestCase):
    """Test cases for the BundleAdminForm save method when API is disabled."""

    @classmethod
    def setUpTestData(cls):
        cls.form_class = get_edit_handler(Bundle).get_form_class()
        cls.approver = UserFactory()

    def setUp(self):
        self.patcher = patch("cms.bundles.forms.BundleAPIClient")
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

    def tearDown(self):
        self.patcher.stop()

    def test_save_new_bundle_with_datasets_does_not_call_api_when_disabled(self):
        """Test that saving a new bundle with datasets doesn't call the API when disabled."""
        dataset = DatasetFactory(id=123, title="Test Dataset")
        raw_data = {
            "name": "Test Bundle",
            "status": BundleStatus.DRAFT,
            "bundled_pages": inline_formset([]),
            "bundled_datasets": inline_formset([{"dataset": dataset.id}]),
            "teams": inline_formset([]),
        }

        form = self.form_class(data=nested_form_data(raw_data), for_user=self.approver)

        self.assertTrue(form.is_valid())
        bundle = form.save()

        # API should not be called when disabled
        self.mock_client.create_bundle.assert_not_called()
        self.assertIsNone(bundle.bundle_api_id)
