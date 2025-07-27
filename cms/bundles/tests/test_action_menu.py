from unittest import TestCase

from django.forms import Media
from wagtail.coreutils import get_dummy_request

from cms.bundles.action_menu import (
    ApproveMenuItem,
    BundleActionMenu,
    CreateMenuItem,
    ManualPublishMenuItem,
    ReturnToDraftMenuItem,
    ReturnToInPreviewMenuItem,
    SaveAsDraftMenuItem,
    SaveMenuItem,
    SaveToInPreviewMenuItem,
)
from cms.bundles.tests.factories import BundleFactory


class BundleActionMenuTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.draft_bundle = BundleFactory()
        cls.in_review_bundle = BundleFactory(in_review=True)
        cls.approved_scheduled_bundle = BundleFactory(approved=True)
        cls.approved_manual_bundle = BundleFactory(approved=True, publication_date=None)
        cls.published_bundle = BundleFactory(published=True)

        cls.request = get_dummy_request()

    def test_action_menu_item__context(self):
        context = {
            "label": "Save as draft",
            "label_progress": "Saving…",
            "use_shortcut": True,
            "name": "action-create",
            "classname": "",
            "icon_name": "draft",
            "request": None,
            "bundle": None,
        }

        action_menu_item = CreateMenuItem()
        self.assertEqual(action_menu_item.get_context_data(), context)

        expanded_context = context.copy()
        expanded_context["request"] = self.request
        expanded_context["bundle"] = self.draft_bundle
        self.assertEqual(
            action_menu_item.get_context_data({"request": self.request, "bundle": self.draft_bundle}), expanded_context
        )

    def test_action_menu_items__no_bundle(self):
        action_menu = BundleActionMenu(request=self.request, bundle=None)
        self.assertEqual(len(action_menu.menu_items), 0)
        self.assertIsInstance(action_menu.default_item, CreateMenuItem)

    def test_action_menu_items__draft_bundle(self):
        action_menu = BundleActionMenu(request=self.request, bundle=self.draft_bundle)
        self.assertEqual(len(action_menu.menu_items), 1)
        self.assertIsInstance(action_menu.menu_items[0], SaveToInPreviewMenuItem)
        self.assertIsInstance(action_menu.default_item, SaveAsDraftMenuItem)

    def test_action_menu_items__bundle_in_preview(self):
        action_menu = BundleActionMenu(request=self.request, bundle=self.in_review_bundle)
        self.assertEqual(len(action_menu.menu_items), 2)
        self.assertIsInstance(action_menu.menu_items[0], ApproveMenuItem)
        self.assertIsInstance(action_menu.menu_items[1], ReturnToDraftMenuItem)
        self.assertIsInstance(action_menu.default_item, SaveMenuItem)

    def test_action_menu_items__approved_scheduled_bundle(self):
        action_menu = BundleActionMenu(request=self.request, bundle=self.approved_scheduled_bundle)
        self.assertEqual(len(action_menu.menu_items), 1)
        self.assertIsInstance(action_menu.menu_items[0], ReturnToInPreviewMenuItem)
        self.assertIsInstance(action_menu.default_item, ReturnToDraftMenuItem)

    def test_action_menu_items__approved_but_manual_bundle(self):
        action_menu = BundleActionMenu(request=self.request, bundle=self.approved_manual_bundle)
        self.assertEqual(len(action_menu.menu_items), 2)
        self.assertIsInstance(action_menu.menu_items[0], ManualPublishMenuItem)
        self.assertIsInstance(action_menu.menu_items[1], ReturnToInPreviewMenuItem)
        self.assertIsInstance(action_menu.default_item, ReturnToDraftMenuItem)

    def test_action_menu_items__published_bundle(self):
        action_menu = BundleActionMenu(request=self.request, bundle=self.published_bundle)
        self.assertEqual(action_menu.menu_items, [])
        self.assertIsNone(action_menu.default_item)

    def test_action_menu__render_html__no_items(self):
        action_menu = BundleActionMenu(request=self.request, bundle=self.published_bundle)
        self.assertEqual(action_menu.render_html(), "")

    def test_action_menu__render_html__new_bundle(self):
        action_menu = BundleActionMenu(request=self.request, bundle=None)
        rendered = action_menu.render_html()
        self.assertIn('value="action-create"', rendered)
        self.assertIn("Save as draft", rendered)

    def test_action_menu__render_html__draft_bundle(self):
        action_menu = BundleActionMenu(request=self.request, bundle=self.draft_bundle)
        rendered = action_menu.render_html()
        self.assertIn('value="action-edit"', rendered)
        self.assertIn("Save as draft", rendered)

        self.assertIn('value="action-save-to-preview"', rendered)
        self.assertIn("Save to preview", rendered)

    def test_action_menu__media(self):
        action_menu = BundleActionMenu(request=self.request, bundle=None)
        self.assertIsInstance(action_menu.media, Media)
