from datetime import date

from django.test import TestCase, override_settings
from django.utils.translation import gettext

from cms.core.tests.utils import TranslationResetMixin
from cms.release_calendar.utils import get_translated_string, parse_month_year


class ParseMonthYearTestCase(TestCase):
    def test_parse_month_year(self):
        cases = [
            ("January 2023", "en", date(2023, 1, 1)),
            ("February 2023", "en", date(2023, 2, 1)),
            ("Mar 2023", "en", None),
            ("May 2023", "en", date(2023, 5, 1)),
            ("January 2023", "cy", None),
            ("Ionawr 2023", "cy", date(2023, 1, 1)),
            ("Chwefror 2023", "cy", date(2023, 2, 1)),
            ("Mawrth 2023", "cy", date(2023, 3, 1)),
            ("April 2023", "ja", None),
            ("April 23", "en", None),
            ("April Problematic", "en", None),
            ("2023 April", "en", None),
            ("", "", None),
            ("", "en", None),
        ]
        for text, locale, parse_result in cases:
            with self.subTest(text=text, locale=locale, parse_result=parse_result):
                self.assertEqual(parse_month_year(text, locale), parse_result)


class GetTranslatedStringTestCase(TranslationResetMixin, TestCase):
    def test_get_translated_string_with_english(self):
        """Test translation to English language."""
        test_string = "Hello"
        result = get_translated_string(test_string, "en")
        self.assertEqual(result, "Hello")

    def test_get_translated_string_with_welsh(self):
        """Test translation to Welsh language."""
        test_string = "Hello"
        result = get_translated_string(test_string, "cy")
        # The function should return the string (translated if available, original if not)
        self.assertIsInstance(result, str)
        self.assertGreaterEqual(len(result), 0)

    def test_get_translated_string_with_actual_translation(self):
        """Test translation with a string that has an actual Welsh translation."""
        # This string has a known translation in the Welsh .po file
        english_string = "Not the latest release"
        expected_welsh = "Nid y datganiad diweddaraf"

        # Test English (should return original)
        english_result = get_translated_string(english_string, "en")
        self.assertEqual(english_result, english_string)

        # Test Welsh (should return translation)
        welsh_result = get_translated_string(english_string, "cy")
        self.assertEqual(welsh_result, expected_welsh)

    def test_get_translated_string_with_unsupported_language(self):
        """Test translation with an unsupported language code."""
        test_string = "Hello"
        result = get_translated_string(test_string, "fr")
        # Should return the original string if no translation is available
        self.assertEqual(result, "Hello")

    def test_get_translated_string_with_empty_string(self):
        """Test translation with empty string."""
        test_string = ""
        result = get_translated_string(test_string, "en")
        self.assertEqual(result, "")

    def test_get_translated_string_preserves_context(self):
        """Test that translation context is properly isolated."""
        test_string = "Not the latest release"  # This string has a known translation

        # Get translation in English
        english_result = get_translated_string(test_string, "en")

        # Get translation in Welsh
        welsh_result = get_translated_string(test_string, "cy")

        # Verify the function doesn't affect global translation context
        # by checking that gettext still works with the original context
        current_translation = gettext(test_string)

        # Both calls should return valid strings
        self.assertIsInstance(welsh_result, str)
        self.assertIsInstance(english_result, str)
        self.assertIsInstance(current_translation, str)

        # Ensure the Welsh and English translations are different
        # and that the current translation is the English one
        self.assertNotEqual(english_result, welsh_result)
        self.assertEqual(current_translation, english_result)

    def test_get_translated_string_with_special_characters(self):
        """Test translation with strings containing special characters."""
        test_cases = [
            "String with numbers 123",
            "String with symbols !@#$%",
            "String with unicode: café",
            "String with newlines\nand tabs\t",
        ]

        for test_string in test_cases:
            with self.subTest(test_string=test_string):
                result_en = get_translated_string(test_string, "en")
                result_cy = get_translated_string(test_string, "cy")

                # Should handle special characters without errors
                self.assertIsInstance(result_en, str)
                self.assertIsInstance(result_cy, str)

    @override_settings(USE_I18N=False)
    def test_get_translated_string_with_i18n_disabled(self):
        """Test behavior when internationalization is disabled."""
        test_string = "Hello world"
        result = get_translated_string(test_string, "cy")
        # Should still return a string even when i18n is disabled
        self.assertEqual(result, "Hello world")
