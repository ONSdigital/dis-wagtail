from django.core.exceptions import ValidationError
from django.test import TestCase

from cms.core.blocks.struct_blocks import RelativeOrAbsoluteURLBlock


class RelativeOrAbsoluteURLBlockTestCase(TestCase):
    def test_invalid_url(self):
        block = RelativeOrAbsoluteURLBlock()
        with self.assertRaises(ValidationError):
            block.clean("example/invalid/url")

    def test_absolute_url(self):
        block = RelativeOrAbsoluteURLBlock()
        valid_absolute_url = "https://www.example.com/some/path"
        cleaned_value = block.clean(valid_absolute_url)
        self.assertEqual(cleaned_value, valid_absolute_url)

    def test_relative_url(self):
        block = RelativeOrAbsoluteURLBlock()
        valid_relative_url = "/some/path/to/resource"
        cleaned_value = block.clean(valid_relative_url)
        self.assertEqual(cleaned_value, valid_relative_url)

    def test_relative_url_custom_max_length(self):
        block = RelativeOrAbsoluteURLBlock(max_length=10)
        with self.assertRaises(ValidationError):
            block.clean("/test/longer/url")

    def test_relative_url_default_max_length(self):
        block = RelativeOrAbsoluteURLBlock()
        long_relative_url = "/" + ("a" * 3000)  # Exceeds Django's default URL max length of 2048
        with self.assertRaises(ValidationError):
            block.clean(long_relative_url)

    def test_relative_url_min_length(self):
        block = RelativeOrAbsoluteURLBlock(min_length=100)
        with self.assertRaises(ValidationError):
            block.clean("/a")

    def test_relative_url_with_unsafe_character(self):
        block = RelativeOrAbsoluteURLBlock()
        unsafe_relative_url = "/some/path/with space"
        with self.assertRaises(ValidationError):
            block.clean(unsafe_relative_url)
