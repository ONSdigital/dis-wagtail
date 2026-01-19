from typing import TYPE_CHECKING
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils import WagtailTestUtils

from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.panels import ReleaseCalendarBundleNotePanel
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory

if TYPE_CHECKING:
    from wagtail.models import Page


class BundleNotePanelTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.page = ReleaseCalendarPageFactory()
        cls.bundle = BundleFactory(name="Test Bundle", status=BundleStatus.DRAFT, release_calendar_page=cls.page)
        cls.panel = ReleaseCalendarBundleNotePanel()
        cls.request = get_dummy_request()
        cls.request.user = cls.superuser

    def get_bound_panel(self, page: Page) -> ReleaseCalendarBundleNotePanel.BoundPanel:
        """Binds the panel to the given page."""
        return self.panel.bind_to_model(page._meta.model).get_bound_panel(instance=page, request=self.request)

    def test_panel_template(self):
        self.assertEqual(self.panel.template, "wagtailadmin/panels/bundle_note_help_panel.html")

    def test_panel__is_shown(self):
        self.assertTrue(self.get_bound_panel(self.page).is_shown())
        del self.page.active_bundle

        self.bundle.status = BundleStatus.PUBLISHED
        self.bundle.save(update_fields=["status"])
        self.assertFalse(self.get_bound_panel(self.page).is_shown())
        del self.page.active_bundle

        self.bundle.release_calendar_page = None
        self.bundle.save(update_fields=["release_calendar_page"])
        self.assertFalse(self.get_bound_panel(self.page).is_shown())

    def test_panel_content_with_active_bundle(self):
        content = self.get_bound_panel(self.page).content

        edit_url = reverse("bundle:edit", args=[self.bundle.pk])
        self.assertTagInHTML(
            f"<p>This page is in the following bundle: "
            f'<a href"{edit_url}">{self.bundle.name} (Status: {BundleStatus.DRAFT.label})</p>',
            content,
        )

    @patch("cms.bundles.panels.user_can_manage_bundles", return_value=False)
    def test_panel_content_when_in_bundle_but_cannot_manage_bundles(self, _mocked_can_manage):
        content = self.get_bound_panel(self.page).content
        self.assertTagInHTML(
            f"<p>This page is in the following bundle: {self.bundle.name} (Status: {BundleStatus.DRAFT.label})</p>",
            content,
        )

    def test_panel_status(self):
        scenarios = [
            (BundleStatus.DRAFT, "info"),
            (BundleStatus.IN_REVIEW, "info"),
            (BundleStatus.APPROVED, "warning"),
        ]
        for bundle_status, panel_status in scenarios:
            with self.subTest(f"Bundle status: {bundle_status}, Panel status: {panel_status}"):
                self.bundle.status = bundle_status
                self.bundle.save(update_fields=["status"])
                self.assertEqual(self.get_bound_panel(self.page).status, panel_status)
                del self.page.active_bundle
