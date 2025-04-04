from typing import TYPE_CHECKING
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from wagtail.coreutils import get_dummy_request
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
        cls.request = get_dummy_request()
        cls.request.user = cls.superuser

    def get_bound_panel(self, page: "Page") -> BundleNotePanel.BoundPanel:
        """Binds the panel to the given page."""
        return self.panel.bind_to_model(page._meta.model).get_bound_panel(instance=page, request=self.request)

    def test_panel_content_without_bundles(self):
        """Test panel content when page is not in any bundles."""
        self.assertIn("This page is not part of any bundles", self.get_bound_panel(self.page).content)

    def test_panel_content_with_bundles(self):
        """Test panel content when page is in bundles."""
        BundlePageFactory(parent=self.bundle, page=self.page)

        content = self.get_bound_panel(self.page).content

        edit_url = reverse("bundle:edit", args=[self.bundle.pk])
        self.assertTagInHTML(
            f"<p>This page is in the following bundle: "
            f'<a href"{edit_url}">{self.bundle.name} (Status: {BundleStatus.PENDING.label})</p>',
            content,
        )

    @patch("cms.bundles.panels.user_can_manage_bundles", return_value=False)
    def test_panel_content_when_in_bundle_but_cannot_manage_bundles(self, _mocked_can_manage):
        BundlePageFactory(parent=self.bundle, page=self.page)

        content = self.get_bound_panel(self.page).content
        self.assertTagInHTML(
            f"<p>This page is in the following bundle: {self.bundle.name} (Status: {BundleStatus.PENDING.label})</p>",
            content,
        )

    def test_panel_content_non_bundled_model(self):
        """Test panel content for non-bundled models."""

        class DummyModel:
            pass

        panel = self.panel.bind_to_model(DummyModel)
        bound_panel = panel.get_bound_panel(instance=DummyModel())
        self.assertEqual(bound_panel.content, "")
