from django.conf import settings
from django.contrib.auth.models import Group
from django.templatetags.static import static
from django.test import TestCase
from django.utils.html import format_html
from wagtail import hooks
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.standard_pages.tests.factories import IndexPageFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_for_review, mark_page_as_ready_to_publish
from cms.workflows.wagtail_hooks import insert_workflow_tweaks_js


class WagtailHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_admin = UserFactory(username="publishing_admin")
        cls.publishing_admin.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))

        cls.index_page = IndexPageFactory(live=False)
        cls.bulk_publish_url = f"/admin/bulk/wagtailcore/page/publish/?id={cls.index_page.pk}"

    def setUp(self):
        self.client.force_login(self.publishing_admin)

    def test_insert_workflow_tweaks_js(self):
        """Test that insert_workflow_tweaks_js returns the expected HTML."""
        # Get the result from the hook function
        result = insert_workflow_tweaks_js()

        # Create the expected HTML
        expected_js_url = static("js/workflow-tweaks.js")
        expected_html = format_html(
            '<script src="{}"></script>',
            expected_js_url,
        )

        # Assert that the result matches the expected HTML
        self.assertEqual(result, expected_html)

        # Assert that the script tag contains the correct URL
        self.assertIn(expected_js_url, result)

    def test_insert_workflow_tweaks_js_registered(self):
        """Test that the insert_workflow_tweaks_js function is registered with the insert_editor_js hook."""
        # Get all functions registered with the insert_editor_js hook
        registered_hooks = hooks.get_hooks("insert_editor_js")

        # Assert that our function is in the list of registered hooks
        self.assertIn(insert_workflow_tweaks_js, registered_hooks)

    def test_bulk_publish_page_override__no_access__not_in_workflow(self):
        response = self.client.get(self.bulk_publish_url)
        self.assertContains(response, "You don't have permission to publish this page")
        self.assertContains(response, self.index_page.title)

    def test_bulk_publish_page_override__in_workflow_but_not_ready_to_publish(self):
        mark_page_as_ready_for_review(self.index_page)
        response = self.client.get(self.bulk_publish_url)
        self.assertContains(response, "You don't have permission to publish this page")
        self.assertContains(response, self.index_page.title)
        self.assertContains(response, "Publish 0 pages")

    def test_bulk_publish_page_override__in_bundle(self):
        bundle = BundleFactory()
        BundlePageFactory(parent=bundle, page=self.index_page)
        bundle.status = BundleStatus.APPROVED
        bundle.save(update_fields=["status"])

        mark_page_as_ready_to_publish(self.index_page)

        response = self.client.get(self.bulk_publish_url)
        self.assertContains(response, "You don't have permission to publish this page")
        self.assertContains(response, self.index_page.title)
        self.assertContains(response, "Publish 0 pages")

    def test_bulk_publish_page_override__ready_to_publish(self):
        mark_page_as_ready_to_publish(self.index_page)
        response = self.client.get(self.bulk_publish_url)
        self.assertNotContains(response, "You don't have permission to publish this page")
        self.assertContains(response, self.index_page.title)
        self.assertContains(response, "Publish 1 page")
