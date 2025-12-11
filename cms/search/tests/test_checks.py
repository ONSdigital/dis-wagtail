from unittest.mock import patch

from django.test import TestCase, override_settings
from wagtail.models import Page

from cms.search.checks import (
    check_kafka_settings,
    check_search_index_content_type,
    check_search_index_included_languages,
)


class KafkaSettingsCheckTests(TestCase):
    def test_not_kafka_backend_no_errors(self):
        """If SEARCH_INDEX_PUBLISHER_BACKEND is not 'kafka', the check should return an empty list."""
        with override_settings(SEARCH_INDEX_PUBLISHER_BACKEND="not_kafka"):
            errors = check_kafka_settings(app_configs=None)
        self.assertEqual(errors, [])

    # Remove any existing KAFKA_* settings if present
    @override_settings(
        SEARCH_INDEX_PUBLISHER_BACKEND="kafka",
        KAFKA_SERVERS=None,
    )
    def test_missing_kafka_settings(self):
        """If SEARCH_INDEX_PUBLISHER_BACKEND='kafka' but required Kafka settings are missing,
        each missing setting should raise an Error with the appropriate id.
        """
        errors = check_kafka_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        error_ids = [error.id for error in errors]
        self.assertIn("search.E001", error_ids)  # Missing KAFKA_SERVERS

    @override_settings(
        SEARCH_INDEX_PUBLISHER_BACKEND="kafka",
        KAFKA_SERVERS="",
    )
    def test_empty_kafka_server_setting(self):
        """If a required Kafka setting is defined but empty, we should get an error
        with the 'empty_id' from the kafka_settings list.
        """
        errors = check_kafka_settings(app_configs=None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "search.E001")
        self.assertIn("KAFKA_SERVERS is missing or empty.", errors[0].msg)
        self.assertIn("Set KAFKA_SERVERS to e.g. 'localhost:9092'.", errors[0].hint)

    @override_settings(
        SEARCH_INDEX_PUBLISHER_BACKEND="kafka",
        KAFKA_SERVERS="localhost:9092",
    )
    def test_no_errors_if_all_kafka_settings_present(self):
        """If SEARCH_INDEX_PUBLISHER_BACKEND='kafka' and all required settings are properly defined,
        there should be no errors.
        """
        errors = check_kafka_settings(app_configs=None)
        self.assertEqual(errors, [])


class SearchIndexContentTypeCheckTests(TestCase):
    """Tests for the check_search_index_content_type system check,
    which requires a 'search_index_content_type' attribute on each page model
    not excluded by SEARCH_INDEX_EXCLUDED_PAGE_TYPES.
    """

    @override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=())
    @patch("cms.search.checks.get_page_models")
    def test_missing_search_index_content_type(self, mock_get_page_models):
        """If a page model is not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        and does not define 'search_index_content_type', we should get an error.
        """

        class MyPageModelWithoutAttrTest1(Page):
            class Meta:
                abstract = True

        mock_get_page_models.return_value = [MyPageModelWithoutAttrTest1]
        errors = check_search_index_content_type(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "search.E002")
        self.assertIn("does not define a 'search_index_content_type'", error.msg)
        self.assertIn("Either add an attribute/property 'search_index_content_type'", error.hint)

    @override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=("MyPageModelWithoutAttrTest2",))
    @patch("cms.search.checks.get_page_models")
    def test_model_excluded_no_error(self, mock_get_page_models):
        """If a page model is listed in SEARCH_INDEX_EXCLUDED_PAGE_TYPES,
        we ignore it even if it doesn't define 'search_index_content_type'.
        """

        class MyPageModelWithoutAttrTest2(Page):
            class Meta:
                abstract = True

        mock_get_page_models.return_value = [MyPageModelWithoutAttrTest2]
        errors = check_search_index_content_type(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=())
    @patch("cms.search.checks.get_page_models")
    def test_model_with_content_type_no_error(self, mock_get_page_models):
        """If a page model defines a search_index_content_type, we should not get any errors."""

        class MyPageModelWithAttr(Page):
            search_index_content_type = "cms.search.my_page_model"

            class Meta:
                abstract = True

        mock_get_page_models.return_value = [MyPageModelWithAttr]
        errors = check_search_index_content_type(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=("SomeOtherModel",))
    @patch("cms.search.checks.get_page_models")
    def test_multiple_page_models_mixed(self, mock_get_page_models):
        """If multiple page models are returned, some excluded, some not,
        ensure only those not excluded and missing the attribute cause errors.
        """

        class IncludedPage(Page):
            # no search_index_content_type
            class Meta:
                abstract = True

        class ExcludedPage(Page):
            # no search_index_content_type but will be excluded
            class Meta:
                abstract = True

        mock_get_page_models.return_value = [IncludedPage, ExcludedPage]

        # Mark 'ExcludedPage' as excluded
        with override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=("ExcludedPage",)):
            errors = check_search_index_content_type(app_configs=None)

        # We expect only 1 error from IncludedPage
        self.assertEqual(len(errors), 1)
        self.assertIn("IncludedPage", errors[0].msg)
        self.assertEqual(errors[0].id, "search.E002")


class SearchIndexIncludedLanguagesCheckTests(TestCase):
    """Tests for the check_search_index_included_languages system check,
    validating SEARCH_INDEX_INCLUDED_LANGUAGES is non-empty, lowercase, and within LANGUAGES.
    """

    @override_settings(
        LANGUAGES=(("en-gb", "English"), ("cy", "Welsh")),
        SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"],
    )
    def test_valid_included_languages_no_errors(self):
        errors = check_search_index_included_languages(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        LANGUAGES=(("en-gb", "English"), ("cy", "Welsh")),
        SEARCH_INDEX_INCLUDED_LANGUAGES=[],
    )
    def test_empty_included_languages_raises_error(self):
        errors = check_search_index_included_languages(app_configs=None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "search.E003")
        self.assertIn("non-empty list", errors[0].msg.lower())

    @override_settings(
        LANGUAGES=(("en-gb", "English"), ("cy", "Welsh")),
        SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "fr"],
    )
    def test_invalid_codes_raises_error(self):
        errors = check_search_index_included_languages(app_configs=None)
        # Expect exactly one error for invalid codes
        self.assertTrue(any(e.id == "search.E004" for e in errors))
        invalid_error = next(e for e in errors if e.id == "search.E004")
        self.assertIn("invalid codes", invalid_error.hint.lower())
        self.assertIn("fr", invalid_error.hint)

    @override_settings(
        LANGUAGES=(("en-gb", "English"), ("cy", "Welsh")),
        SEARCH_INDEX_INCLUDED_LANGUAGES=["EN-GB", "CY"],
    )
    def test_non_lowercase_codes_raises_error(self):
        errors = check_search_index_included_languages(app_configs=None)
        # Expect exactly one error for non-lowercase
        self.assertTrue(any(e.id == "search.E005" for e in errors))
        lowercase_error = next(e for e in errors if e.id == "search.E005")
        self.assertIn("lowercase", lowercase_error.msg.lower())
        self.assertIn("EN-GB", lowercase_error.hint)
        self.assertIn("CY", lowercase_error.hint)
