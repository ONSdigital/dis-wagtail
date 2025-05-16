from collections import defaultdict
from importlib import reload
from unittest import mock

from django.test import SimpleTestCase, override_settings
from wagtail import hooks

from cms.auth import wagtail_hooks


@override_settings(AWS_COGNITO_LOGIN_ENABLED=True)
class WagtailHookEnabledTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        reload(wagtail_hooks)  # re-register hooks with flag ON

    def test_hook_registers_and_outputs_script(self):
        snippets = hooks.get_hooks("insert_global_admin_js")
        self.assertTrue(snippets)  # hook is present

        #  patch staticfiles lookup so missing asset doesn't raise
        with mock.patch(
            "cms.auth.wagtail_hooks.static",
            lambda path: f"/static/{path}",
        ):
            html = "".join(fn() for fn in snippets)

        self.assertIn("window.authConfig", html)
        self.assertIn("/static/js/auth.js", html)


@override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
class WagtailHookDisabledTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # wipe any hooks registered by earlier tests
        hooks._hooks = defaultdict(list)  # pylint: disable=protected-access

        reload(wagtail_hooks)

    def test_hook_is_not_registered(self):
        snippets = hooks.get_hooks("insert_global_admin_js")
        self.assertFalse(snippets)  # list should be empty
