from django.templatetags.static import static
from django.test import TestCase
from django.utils.html import format_html
from wagtail import hooks
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.workflows.wagtail_hooks import insert_workflow_tweaks_js


class WagtailHooksTestCase(WagtailTestUtils, TestCase):
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
