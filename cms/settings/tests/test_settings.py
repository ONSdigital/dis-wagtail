from datetime import datetime

from django.conf import settings
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse_lazy
from django.utils.csp import CSP


class SettingsTestCase(TestCase):
    """Tests for the Referrer-Policy header."""

    def test_referrer_policy(self):
        """Test that we have a Referrer-Policy header."""
        response = self.client.get("/")
        self.assertEqual(response["Referrer-Policy"], "no-referrer-when-downgrade")

    def test_date_format(self):
        """Test that DATETIME_FORMAT is our preferred one."""
        template = Template("{{ date|date:'DATETIME_FORMAT' }}")
        date = datetime(2024, 11, 1, 13, 0)
        self.assertEqual(template.render(Context({"date": date})), "1 November 2024 1:00p.m.")


class CSPTestCase(TestCase):
    urls = frozenset(["/", "/test404", reverse_lazy("wagtailadmin_login")])

    def _parse_csp(self, header_value: str) -> dict[str, list[str]]:
        directives = {}

        for directive in header_value.split(";"):
            parts = directive.strip().split(" ", 1)
            directives[parts[0]] = parts[1].split()

        return directives

    def get_csp_expressions(self, policy: dict[str, list[str]], directive: str) -> list[str]:
        # Fall back to default-src if directive is not present
        return policy.get(directive, policy.get("default-src", []))

    def test_self_in_all_expressions(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                for directive in settings.SECURE_CSP:
                    with self.subTest(directive):
                        self.assertIn(CSP.SELF, self.get_csp_expressions(csp, directive))

    def test_gtm_csp(self):
        """https://developers.google.com/tag-platform/security/guides/csp."""
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn("www.googletagmanager.com", self.get_csp_expressions(csp, "img-src"))
                self.assertIn("www.googletagmanager.com", self.get_csp_expressions(csp, "connect-src"))
                self.assertIn("www.google.com", self.get_csp_expressions(csp, "connect-src"))

    def test_hotjar_csp(self):
        """https://help.hotjar.com/hc/en-us/articles/36820026388881-Content-Security-Policies."""
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)
                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn("*.hotjar.com", self.get_csp_expressions(csp, "img-src"))
                self.assertIn("*.hotjar.com", self.get_csp_expressions(csp, "script-src"))
                self.assertIn(CSP.UNSAFE_INLINE, self.get_csp_expressions(csp, "script-src"))
                self.assertIn("*.hotjar.com", self.get_csp_expressions(csp, "connect-src"))
                self.assertIn("*.hotjar.io", self.get_csp_expressions(csp, "connect-src"))
                self.assertIn("wss://*.hotjar.com", self.get_csp_expressions(csp, "connect-src"))
                self.assertIn("*.hotjar.com", self.get_csp_expressions(csp, "font-src"))
                self.assertIn("*.hotjar.com", self.get_csp_expressions(csp, "style-src"))
                self.assertIn(CSP.UNSAFE_INLINE, self.get_csp_expressions(csp, "style-src"))

    def test_mathjax_csp(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn("cdnjs.cloudflare.com", self.get_csp_expressions(csp, "style-src"))
                self.assertIn(CSP.UNSAFE_INLINE, self.get_csp_expressions(csp, "style-src"))
                self.assertIn("cdnjs.cloudflare.com", self.get_csp_expressions(csp, "script-src"))
                self.assertIn("cdnjs.cloudflare.com", self.get_csp_expressions(csp, "font-src"))

    def test_design_system_csp(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                self.assertIn(settings.ONS_CDN_URL, self.get_csp_expressions(csp, "style-src"))
                self.assertIn(settings.ONS_CDN_URL, self.get_csp_expressions(csp, "script-src"))
                self.assertIn(settings.ONS_CDN_URL, self.get_csp_expressions(csp, "font-src"))
                self.assertIn(settings.ONS_CDN_URL, self.get_csp_expressions(csp, "manifest-src"))

    def test_iframe_visualisation_csp(self):
        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                csp = self._parse_csp(response.headers["Content-Security-Policy"])

                for allowed_domain in settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS:
                    with self.subTest(allowed_domain):
                        self.assertIn(allowed_domain, self.get_csp_expressions(csp, "frame-src"))

    def test_wagtail_csp(self):
        """https://github.com/wagtail/wagtail/issues?q=is%3Aissue%20state%3Aopen%20csp."""
        response = self.client.get(reverse_lazy("wagtailadmin_login"))

        csp = self._parse_csp(response.headers["Content-Security-Policy"])

        self.assertIn(CSP.UNSAFE_INLINE, self.get_csp_expressions(csp, "script-src"))
