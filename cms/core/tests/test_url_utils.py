from django.forms import ValidationError
from django.test import TestCase, override_settings

from cms.core.url_utils import is_hostname_in_domain, normalise_url, validate_ons_url


class TestIsHostnameInDomain(TestCase):
    def tests_hostname_in_domain_positive_cases(self):
        test_cases = [
            ("example.com", "example.com"),
            ("sub.example.com", "example.com"),
            ("another.subdomain.example.com", "example.com"),
        ]

        for hostname_domain_pair in test_cases:
            with self.subTest():
                self.assertTrue(is_hostname_in_domain(*hostname_domain_pair))

    def test_is_hostname_in_domain_negative_cases(self):
        test_cases = [
            ("example.domain.com", "example.com"),
            ("other.com", "example.com"),
            ("", "example.com"),
            ("example.com", ""),
        ]

        for hostname_domain_pair in test_cases:
            with self.subTest():
                self.assertFalse(is_hostname_in_domain(*hostname_domain_pair))


class TestValidateONSUrl(TestCase):
    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_valid_ons_url(self):
        url = "https://example.com/page"
        errors = validate_ons_url(url)
        self.assertEqual(errors, {})

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_url_on_disallowed_domain(self):
        url = "https://not-allowed-domain.com/page"
        errors = validate_ons_url(url)
        self.assertIn("url", errors)
        self.assertIsInstance(errors["url"], ValidationError)
        self.assertEqual(
            errors["url"].message,
            "The URL hostname is not in the list of allowed domains or their subdomains: example.com",
        )

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_url_no_https_in_url(self):
        url = "http://example.com/page"
        errors = validate_ons_url(url)
        self.assertIn("url", errors)
        self.assertIsInstance(errors["url"], ValidationError)
        self.assertEqual(
            errors["url"].message,
            "Please enter a valid URL. It should start with 'https://' and contain a valid domain name.",
        )


class TestNormaliseUrl(TestCase):
    def test_strips_trailing_slash(self):
        url_with_slash = "https://example.com/"
        url_without_slash = "https://example.com"
        self.assertEqual(normalise_url(url_with_slash), normalise_url(url_without_slash))

    def test_removes_https_and_www_prefixes(self):
        url_with_prefixes = "https://www.example.com"
        url_without_prefixes = "example.com"
        self.assertEqual(normalise_url(url_with_prefixes), normalise_url(url_without_prefixes))
