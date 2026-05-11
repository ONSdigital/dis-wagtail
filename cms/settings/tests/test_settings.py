import importlib
import os
from datetime import datetime
from unittest import mock

from django.template import Context, Template
from django.test import TestCase

from cms.settings import base


class SettingsTestCase(TestCase):
    """Test that our settings are as expected."""

    def test_referrer_policy(self):
        """Test that we have a Referrer-Policy header."""
        response = self.client.get("/")
        self.assertEqual(response["Referrer-Policy"], "no-referrer-when-downgrade")

    def test_date_format(self):
        """Test that DATETIME_FORMAT is our preferred one."""
        template = Template("{{ date|date:'DATETIME_FORMAT' }}")
        date = datetime(2024, 11, 1, 13, 0)
        self.assertEqual(template.render(Context({"date": date})), "1 November 2024 1:00p.m.")

    def test_default_wagtail_admin_login_url_uses_home_path(self):
        """Test that the default login URL is derived from the home path."""
        with mock.patch.dict(os.environ, {"WAGTAILADMIN_HOME_PATH": "cms-admin/"}, clear=True):
            self.addCleanup(importlib.reload, base)
            reloaded_base = importlib.reload(base)
            self.assertEqual(reloaded_base.WAGTAILADMIN_HOME_PATH, "cms-admin/")
            self.assertEqual(reloaded_base.WAGTAILADMIN_LOGIN_URL, "/cms-admin/login/")
