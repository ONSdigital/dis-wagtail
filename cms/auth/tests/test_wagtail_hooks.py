# tests/test_wagtail_hooks.py
from django.test import SimpleTestCase, override_settings
from wagtail import hooks


@override_settings(AWS_COGNITO_LOGIN_ENABLED=True)
class WagtailHookTests(SimpleTestCase):
    def test_hook_returns_script_block(self):
        # hooks are registered at import, so just retrieve
        html_snippets = hooks.get_hooks("insert_global_admin_js")
        self.assertTrue(html_snippets)  # at least one
        output = "".join(func() for func in html_snippets)
        self.assertIn("window.authConfig", output)
        self.assertIn("js/auth.js", output)


@override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
class WagtailHookDisabledTests(SimpleTestCase):
    def test_hook_not_registered(self):
        html_snippets = hooks.get_hooks("insert_global_admin_js")
        self.assertFalse(html_snippets)  # nothing registered
