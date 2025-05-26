import json
import re
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

        # Should have the data-island <script id="auth-config">
        self.assertIn('<script id="auth-config"', html, 'Expected a <script id="auth-config"> data-island')

        # Should still load the auth bundle
        self.assertIn("/static/js/auth.js", html, "Expected the auth.js bundle to be included via static()")

    # Rendered JSON payload is exactly what get_auth_config() returns
    def test_rendered_auth_config_matches_helper_output(self):
        expected_json = wagtail_hooks.get_auth_config()
        with mock.patch(
            "cms.auth.wagtail_hooks.static",
            lambda path: f"/static/{path}",
        ):
            html = "".join(fn() for fn in hooks.get_hooks("insert_global_admin_js"))

        # Extract the JSON out of the <script id="auth-config">…</script> data-island
        pattern = r'<script[^>]+id=["\']auth-config["\'][^>]*>(?P<json>.*?)</script>'
        match = re.search(pattern, html, re.S)
        self.assertIsNotNone(match, "auth-config data-island not found in HTML")

        # Raw inner text
        rendered_json = match.group("json").strip()

        # First decode: might be a dict (if get_auth_config ever returns one) or a str
        obj = json.loads(rendered_json)
        # If double-encoded, unwrap again
        if isinstance(obj, str):
            obj = json.loads(obj)

        # Load expected into a dict if it's still a string
        expected_obj = json.loads(expected_json) if isinstance(expected_json, str) else expected_json

        self.assertEqual(
            obj,
            expected_obj,
            msg="Hook rendered JSON that differs from get_auth_config() result",
        )


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
