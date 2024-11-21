from typing import Any

from django import forms
from django.test import TestCase
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.analysis.tests.factories import AnalysisPageFactory
from cms.bundles.admin_forms import AddToBundleForm
from cms.bundles.enums import ACTIVE_BUNDLE_STATUS_CHOICES, BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.viewsets import BundleChooserWidget
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.users.tests.factories import UserFactory


class AddToBundleFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="First Bundle")
        cls.non_editable_bundle = BundleFactory(approved=True)
        cls.page = AnalysisPageFactory(title="The Analysis")

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
        form = AddToBundleForm(page_to_add=ReleaseCalendarPageFactory(), data={"bundle": self.bundle.pk})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, ["Pages of this type cannot be added."])


class BundleAdminFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="First Bundle")
        cls.page = AnalysisPageFactory(title="The Analysis")
        cls.form_class = get_edit_handler(Bundle).get_form_class()

    def setUp(self):
        self.form_data = nested_form_data(self.raw_form_data())

    def raw_form_data(self) -> dict[str, Any]:
        """Returns raw form data."""
        return {
            "name": "First Bundle",
            "status": BundleStatus.IN_REVIEW,
            "bundled_pages": inline_formset([]),
        }

    def test_form_init__status_choices(self):
        """Checks status choices variation."""
        cases = [
            (BundleStatus.PENDING, ACTIVE_BUNDLE_STATUS_CHOICES),
            (BundleStatus.IN_REVIEW, ACTIVE_BUNDLE_STATUS_CHOICES),
            (BundleStatus.APPROVED, BundleStatus.choices),
            (BundleStatus.RELEASED, BundleStatus.choices),
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
        fields = {field: True for field in form.fields}
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
        data = nested_form_data(raw_data)

        form = self.form_class(instance=self.bundle, data=data)
        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, ["'The Analysis' is already in an active bundle (Another Bundle)"])

    def test_clean__sets_approved_by_and_approved_at(self):
        """Checks that Bundle gets the approver and approval time set."""
        approver = UserFactory()

        data = self.form_data
        data["status"] = BundleStatus.APPROVED
        form = self.form_class(instance=self.bundle, data=data, for_user=approver)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["approved_by"], approver)
