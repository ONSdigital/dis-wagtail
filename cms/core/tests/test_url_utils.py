from django.forms import ValidationError
from django.test import TestCase, override_settings
from wagtail.blocks import CharBlock, StructBlock, URLBlock

from cms.core.url_utils import (
    extract_url_path,
    is_hostname_in_domain,
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
    def test_valid_ons_url_and_relative_urls_allowed(self):
        url = "https://example.com/page"
        error = validate_ons_url(url, allow_relative_urls=True)
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

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_url_no_https_in_url_and_relative_urls_allowed(self):
        url = "http://example.com/page"
        error = validate_ons_url(url, allow_relative_urls=True)
        self.assertIsInstance(error, ValidationError)
        self.assertEqual(
            error.message,
            "Please enter a valid URL. It should be a root-relative link or "
            "start with 'https://' and contain a valid domain name.",
        )

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_relative_url_is_allowed(self):
        url = "/releases/foo"
        self.assertIsNone(validate_ons_url(url, allow_relative_urls=True))

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=[""])
    def test_relative_url_is_allowed_when_no_domains_allowed(self):
        url = "/releases/foo"
        self.assertIsNone(validate_ons_url(url, allow_relative_urls=True))

    def test_relative_url_is_not_allowed_when_allow_relative_urls_false(self):
        url = "/releases/foo"
        error = validate_ons_url(url, allow_relative_urls=False)
        self.assertIsInstance(error, ValidationError)
        self.assertEqual(
            error.message,
            "Please enter a valid URL. It should start with 'https://' and contain a valid domain name.",
        )

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_non_root_relative_url_is_not_allowed(self):
        url = "releases/foo"
        error = validate_ons_url(url, allow_relative_urls=True)
        self.assertIsInstance(error, ValidationError)
        self.assertEqual(
            error.message,
            "Please enter a valid URL. It should be a root-relative link or "
            "start with 'https://' and contain a valid domain name.",
        )

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_protocol_relative_and_repeated_slashes_are_not_treated_as_relative(self):
        for url in ("//evil.com/foo", "////abc", "//", "/hello//world"):
            with self.subTest(url=url):
                error = validate_ons_url(url, allow_relative_urls=True)
                self.assertIsInstance(error, ValidationError)


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
            "Please enter a valid URL. It should be a root-relative link or "
            "start with 'https://' and contain a valid domain name.",
        )

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_happy_path(self):
        block = self.TestBlock()
        value = {"title": "Test Title", "url": "https://example.com"}

        errors = validate_ons_url_struct_block(value, block.child_blocks)

        self.assertEqual(errors, {})

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_relative_url_passes(self):
        block = self.TestBlock()
        value = {"title": "Test Title", "url": "/releases/foo"}

        errors = validate_ons_url_struct_block(value, block.child_blocks)

        self.assertEqual(errors, {})


class TestGetUrlPath(TestCase):
    def test_extract_url_path(self):
        test_cases = [
            ("https://example.com/path/to/resource", "/path/to/resource"),
            ("https://example.com/path/with/trailing/slash/", "/path/with/trailing/slash"),
            ("https://example.com/", ""),
            ("https://example.com", ""),
        ]

        for url, expected_path in test_cases:
            with self.subTest(url=url):
                self.assertEqual(extract_url_path(url), expected_path)
