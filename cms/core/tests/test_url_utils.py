from django.forms import ValidationError
from django.test import TestCase, override_settings
from wagtail.blocks import CharBlock, StructBlock, URLBlock

from cms.core.url_utils import (
    extract_url_path,
    is_hostname_in_domain,
    normalise_url,
    validate_ons_url,
    validate_ons_url_struct_block,
)


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
        error = validate_ons_url(url)
        self.assertEqual(error, None)

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_url_on_disallowed_domain(self):
        url = "https://not-allowed-domain.com/page"
        error = validate_ons_url(url)

        self.assertIsInstance(error, ValidationError)
        self.assertEqual(
            error.message,
            "The URL hostname is not in the list of allowed domains or their subdomains: example.com",
        )

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_url_no_https_in_url(self):
        url = "http://example.com/page"
        error = validate_ons_url(url)
        self.assertIsInstance(error, ValidationError)
        self.assertEqual(
            error.message,
            "Please enter a valid URL. It should start with 'https://' and contain a valid domain name.",
        )


class TestValidateONSUrlBlock(TestCase):
    """Test validation of a StructBlock that contains a URL field which is restricted to ONS domain."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class TestBlock(StructBlock):
            title = CharBlock(required=True)
            url = URLBlock(required=True)

        cls.TestBlock = TestBlock

    def test_missing_required_fields(self):
        block = self.TestBlock()
        value = {"title": "", "url": "https://example.com"}

        errors = validate_ons_url_struct_block(value, block.child_blocks)

        self.assertIn("title", errors)
        self.assertIsInstance(errors["title"], ValidationError)
        self.assertEqual(errors["title"].message, "This field is required.")

    def test_incorrect_ons_url(self):
        block = self.TestBlock()
        value = {"title": "Test Title", "url": "incorrect url"}

        errors = validate_ons_url_struct_block(value, block.child_blocks)

        self.assertIn("url", errors)
        self.assertIsInstance(errors["url"], ValidationError)
        self.assertEqual(
            errors["url"].message,
            "Please enter a valid URL. It should start with 'https://' and contain a valid domain name.",
        )

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_happy_path(self):
        block = self.TestBlock()
        value = {"title": "Test Title", "url": "https://example.com"}

        errors = validate_ons_url_struct_block(value, block.child_blocks)

        self.assertEqual(errors, {})


class TestNormaliseUrl(TestCase):
    def test_strips_trailing_slash(self):
        url_with_slash = "https://example.com/"
        url_without_slash = "https://example.com"
        self.assertEqual(normalise_url(url_with_slash), normalise_url(url_without_slash))

    def test_removes_https_and_www_prefixes(self):
        url_with_prefixes = "https://www.example.com"
        url_without_prefixes = "example.com"
        self.assertEqual(normalise_url(url_with_prefixes), normalise_url(url_without_prefixes))


class TestGetUrlPath(TestCase):
    def test_extract_url_path(self):
        test_cases = [
            ("https://example.com/path/to/resource", "/path/to/resource"),
            ("https://example.com/path/with/trailing/slash/", "/path/with/trailing/slash"),
            ("https://example.com/path/WITH/CAPS", "/path/with/caps"),
            ("https://example.com/", ""),
            ("https://example.com", ""),
        ]

        for url, expected_path in test_cases:
            with self.subTest(url=url):
                self.assertEqual(extract_url_path(url), expected_path)
