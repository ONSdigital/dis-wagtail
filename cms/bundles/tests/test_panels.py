from typing import TYPE_CHECKING

from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.panels import BundleNotePanel
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory

if TYPE_CHECKING:
    from wagtail.models import Page


class BundleNotePanelTestCase(WagtailTestUtils, TestCase):
    """Test BundleNotePanel functionality."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.page = StatisticalArticlePageFactory()
        cls.bundle = BundleFactory(name="Test Bundle", status=BundleStatus.PENDING)
        cls.panel = BundleNotePanel()

    def get_bound_panel(self, page: "Page") -> BundleNotePanel.BoundPanel:
        """Binds the panel to the given page."""
        return self.panel.bind_to_model(page._meta.model).get_bound_panel(instance=page)

    def test_panel_content_without_bundles(self):
        """Test panel content when page is not in any bundles."""
        self.assertIn("This page is not part of any bundles", self.get_bound_panel(self.page).content)

    def test_panel_content_with_bundles(self):
        """Test panel content when page is in bundles."""
        BundlePageFactory(parent=self.bundle, page=self.page)

        content = self.get_bound_panel(self.page).content

        self.assertIn("This page is in the following bundle(s):", content)
        self.assertIn("Test Bundle", content)
        self.assertIn("Status: Pending", content)

    def test_panel_content_non_bundled_model(self):
        """Test panel content for non-bundled models."""

        class DummyModel:
            pass

        panel = self.panel.bind_to_model(DummyModel)
        bound_panel = panel.get_bound_panel(instance=DummyModel())
        self.assertEqual(bound_panel.content, "")
