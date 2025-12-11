from typing import TYPE_CHECKING
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.panels import BundleDatasetChooserWidget, BundleMultipleChooserPanel, BundleNotePanel
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory

if TYPE_CHECKING:
    from wagtail.models import Page


class BundleNotePanelTestCase(WagtailTestUtils, TestCase):
    """Test BundleNotePanel functionality."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.page = StatisticalArticlePageFactory()
        cls.bundle = BundleFactory(name="Test Bundle", status=BundleStatus.DRAFT)
        cls.panel = BundleNotePanel()
        cls.request = get_dummy_request()
        cls.request.user = cls.superuser

    def get_bound_panel(self, page: "Page") -> BundleNotePanel.BoundPanel:
        """Binds the panel to the given page."""
        return self.panel.bind_to_model(page._meta.model).get_bound_panel(instance=page, request=self.request)

    def test_panel_content_without_bundles(self):
        """Test panel content when page is not in any bundles."""
        content = self.get_bound_panel(self.page).content
        self.assertIn("This page is not part of any bundles", content)

        # note: next=/ comes from the fact that this is a dummy request.
        url = reverse("bundles:add_to_bundle", args=(self.page.pk,), query={"next": "/"})
        self.assertIn(f'<a href="{url}" class="button button-small button-secondary">Add to Bundle</a></p>', content)

    @patch("cms.bundles.panels.user_can_manage_bundles", return_value=False)
    def test_panel_content_without_bundles__if_user_cannot_manage(self, _mock_can_manage_bundles):
        """Test panel content when page is not in any bundles."""
        content = self.get_bound_panel(self.page).content
        self.assertIn("This page is not part of any bundles", content)

        url = reverse("bundles:add_to_bundle", args=(self.page.pk,))
        self.assertNotIn(f'<a href="{url}" class="button button-small button-secondary">Add to Bundle</a></p>', content)

    def test_panel_content_with_bundles(self):
        """Test panel content when page is in bundles."""
        BundlePageFactory(parent=self.bundle, page=self.page)

        content = self.get_bound_panel(self.page).content

        edit_url = reverse("bundle:edit", args=[self.bundle.pk])
        self.assertTagInHTML(
            f"<p>This page is in the following bundle: "
            f'<a href"{edit_url}">{self.bundle.name} (Status: {BundleStatus.DRAFT.label})</p>',
            content,
        )

    @patch("cms.bundles.panels.user_can_manage_bundles", return_value=False)
    def test_panel_content_when_in_bundle_but_cannot_manage_bundles(self, _mocked_can_manage):
        BundlePageFactory(parent=self.bundle, page=self.page)

        content = self.get_bound_panel(self.page).content
        self.assertTagInHTML(
            f"<p>This page is in the following bundle: {self.bundle.name} (Status: {BundleStatus.DRAFT.label})</p>",
            content,
        )

    def test_panel_content_non_bundled_model(self):
        """Test panel content for non-bundled models."""

        class DummyModel:
            pass

        panel = self.panel.bind_to_model(DummyModel)
        bound_panel = panel.get_bound_panel(instance=DummyModel())
        self.assertEqual(bound_panel.content, "")


class BundleMultipleChooserPanelTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.page = StatisticalArticlePageFactory()
        cls.bundle = BundleFactory(name="Test Bundle", status=BundleStatus.DRAFT)
        cls.panel = BundleMultipleChooserPanel("bundled_pages", chooser_field_name="page")
        cls.request = get_dummy_request()
        cls.request.user = cls.superuser
        BundlePageFactory(parent=cls.bundle, page=cls.page)

    def get_bound_panel(self, bundle: "Bundle") -> BundleMultipleChooserPanel.BoundPanel:
        """Binds the panel to the given page."""
        return self.panel.bind_to_model(bundle._meta.model).get_bound_panel(instance=bundle, request=self.request)

    def test_default_is_not_read_only(self):
        bound_panel = self.get_bound_panel(self.bundle)
        self.assertFalse(bound_panel.read_only)

    def test_marked_as_read_only(self):
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])

        bound_panel = self.get_bound_panel(self.bundle)
        self.assertTrue(bound_panel.read_only)


class BundleDatasetChooserPanelTestCase(TestCase):
    """Test BundleMultipleChooserPanel with bundled_datasets."""

    def test_custom_widget_injected_for_bundled_datasets(self):
        """Test that BundleDatasetChooserWidget is used for bundled_datasets panel."""
        panel = BundleMultipleChooserPanel("bundled_datasets", chooser_field_name="dataset")
        bound_panel_class = panel.bind_to_model(Bundle)

        form_options = bound_panel_class.get_form_options()

        # Verify that our custom widget is in the form options
        formset_opts = form_options["formsets"]["bundled_datasets"]
        self.assertIn("widgets", formset_opts)
        self.assertIn("dataset", formset_opts["widgets"])
        self.assertIsInstance(formset_opts["widgets"]["dataset"], BundleDatasetChooserWidget)

    def test_custom_widget_not_injected_for_other_panels(self):
        """Test that BundleDatasetChooserWidget is NOT used for non-dataset panels."""
        panel = BundleMultipleChooserPanel("bundled_pages", chooser_field_name="page")
        bound_panel_class = panel.bind_to_model(Bundle)

        form_options = bound_panel_class.get_form_options()

        # Verify that BundleDatasetChooserWidget is not used
        formset_opts = form_options["formsets"]["bundled_pages"]
        widget = formset_opts.get("widgets", {}).get("page")
        self.assertNotIsInstance(widget, BundleDatasetChooserWidget)

    def test_bundle_dataset_chooser_widget_url(self):
        """Test that BundleDatasetChooserWidget adds for_bundle parameter to URL."""
        widget = BundleDatasetChooserWidget()
        chooser_url = widget.get_chooser_modal_url()

        # Verify that for_bundle=true is in the URL
        self.assertIn("for_bundle=true", chooser_url)
