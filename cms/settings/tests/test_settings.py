import importlib
import os
from datetime import datetime
from unittest import mock

from django.conf import settings
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.utils.csp import CSP

from cms.home.models import HomePage
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


class CSPTestCase(TestCase):
    urls = frozenset(["/", "/test404", reverse_lazy("wagtailadmin_login")])

    def _parse_csp(self, header_value: str) -> dict[str, list[str]]:
        directives = {}

        for directive in header_value.split(";"):
            parts = directive.strip().split(" ", 1)
            directives[parts[0]] = parts[1].split()

        return directives

    def _get_csp_expressions(self, policy: dict[str, list[str]], directive: str) -> list[str]:
        # Fall back to default-src if directive is not present
        return policy.get(directive, policy.get("default-src", []))

    def test_self_in_all_expressions(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                for directive in settings.SECURE_CSP:
                    with self.subTest(directive):
                        self.assertIn(CSP.SELF, self._get_csp_expressions(csp, directive))

    def test_gtm_csp(self):
        """https://developers.google.com/tag-platform/security/guides/csp."""
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn("www.googletagmanager.com", self._get_csp_expressions(csp, "img-src"))
                self.assertIn("www.googletagmanager.com", self._get_csp_expressions(csp, "connect-src"))
                self.assertIn("www.googletagmanager.com", self._get_csp_expressions(csp, "script-src"))
                self.assertIn("www.google.com", self._get_csp_expressions(csp, "connect-src"))
                self.assertIn("www.googletagmanager.com", self._get_csp_expressions(csp, "connect-src"))

    def test_hotjar_csp(self):
        """https://help.hotjar.com/hc/en-us/articles/36820026388881-Content-Security-Policies."""
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)
                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn("*.hotjar.com", self._get_csp_expressions(csp, "img-src"))
                self.assertIn("*.hotjar.com", self._get_csp_expressions(csp, "script-src"))
                self.assertIn(CSP.UNSAFE_INLINE, self._get_csp_expressions(csp, "script-src"))
                self.assertIn("*.hotjar.com", self._get_csp_expressions(csp, "connect-src"))
                self.assertIn("*.hotjar.io", self._get_csp_expressions(csp, "connect-src"))
                self.assertIn("wss://*.hotjar.com", self._get_csp_expressions(csp, "connect-src"))
                self.assertIn("*.hotjar.com", self._get_csp_expressions(csp, "font-src"))
                self.assertIn("*.hotjar.com", self._get_csp_expressions(csp, "style-src"))
                self.assertIn(CSP.UNSAFE_INLINE, self._get_csp_expressions(csp, "style-src"))

    def test_mathjax_csp(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn("cdnjs.cloudflare.com", self._get_csp_expressions(csp, "style-src"))
                self.assertIn(CSP.UNSAFE_INLINE, self._get_csp_expressions(csp, "style-src"))
                self.assertIn("cdnjs.cloudflare.com", self._get_csp_expressions(csp, "script-src"))
                self.assertIn("cdnjs.cloudflare.com", self._get_csp_expressions(csp, "font-src"))

    def test_design_system_csp(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn(settings.ONS_CDN_URL, self._get_csp_expressions(csp, "style-src"))
                self.assertIn(settings.ONS_CDN_URL, self._get_csp_expressions(csp, "script-src"))
                self.assertIn(settings.ONS_CDN_URL, self._get_csp_expressions(csp, "font-src"))
                self.assertIn(settings.ONS_CDN_URL, self._get_csp_expressions(csp, "manifest-src"))

    def test_iframe_visualisation_csp(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                for allowed_domain in settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS:
                    with self.subTest(allowed_domain):
                        self.assertIn(allowed_domain, self._get_csp_expressions(csp, "frame-src"))

    def test_wagtail_csp(self):
        """https://github.com/wagtail/wagtail/issues?q=is%3Aissue%20state%3Aopen%20csp."""
        response = self.client.get(reverse("wagtailadmin_login"))

        csp = self._parse_csp(response.headers["Content-Security-Policy"])

        self.assertIn(CSP.UNSAFE_INLINE, self._get_csp_expressions(csp, "script-src"))
        self.assertIn(CSP.SELF, self._get_csp_expressions(csp, "frame-ancestors"))

    def test_wagtail_preview_csp(self):
        response = self.client.get(reverse("wagtailadmin_pages:preview_on_edit", args=[HomePage.objects.first().pk]))

        csp = self._parse_csp(response.headers["Content-Security-Policy"])

        self.assertIn(CSP.SELF, self._get_csp_expressions(csp, "frame-ancestors"))

    def test_frame_ancestors(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn(CSP.SELF, self._get_csp_expressions(csp, "frame-ancestors"))

                self.assertNotIn("X-Frame-Options", response.headers)
