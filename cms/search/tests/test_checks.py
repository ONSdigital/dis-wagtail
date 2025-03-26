from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from wagtail.models import Page

from cms.search.checks import check_kafka_settings, check_search_index_content_type


class KafkaSettingsCheckTests(TestCase):
    def test_not_kafka_backend_no_errors(self):
        """If SEARCH_INDEX_PUBLISHER_BACKEND is not 'kafka', the check should return an empty list."""
        with override_settings(SEARCH_INDEX_PUBLISHER_BACKEND="not_kafka"):
            errors = check_kafka_settings(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(SEARCH_INDEX_PUBLISHER_BACKEND="kafka")
    def test_missing_kafka_settings(self):
        """If SEARCH_INDEX_PUBLISHER_BACKEND='kafka' but required Kafka settings are missing,
        each missing setting should raise an Error with the appropriate id.
        """
        # Remove any existing KAFKA_* settings if present
        custom_settings = {
            key: value
            for key, value in settings._wrapped.__dict__.items()  # pylint: disable=protected-access
            if not key.startswith("KAFKA_")
        }
        with self.settings(**custom_settings):
            errors = check_kafka_settings(app_configs=None)

        # Expect 3 missing-settings errors: E002, E004, and E006
        self.assertEqual(len(errors), 3)
        error_ids = [error.id for error in errors]
        self.assertIn("search.E002", error_ids)  # Missing KAFKA_SERVER
        self.assertIn("search.E004", error_ids)  # Missing KAFKA_CHANNEL_CREATED_OR_UPDATED
        self.assertIn("search.E006", error_ids)  # Missing KAFKA_CHANNEL_DELETED

    @override_settings(
        SEARCH_INDEX_PUBLISHER_BACKEND="kafka",
        KAFKA_SERVER="",
        KAFKA_CHANNEL_CREATED_OR_UPDATED="some-topic",
        KAFKA_CHANNEL_DELETED="some-other-topic",
    )
    def test_empty_kafka_server_setting(self):
        """If a required Kafka setting is defined but empty, we should get an error
        with the 'empty_id' from the kafka_settings list.
        """
        errors = check_kafka_settings(app_configs=None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "search.E002")
        self.assertIn("KAFKA_SERVER setting is empty", errors[0].msg)
        self.assertIn("Set KAFKA_SERVER to e.g. 'localhost:9092'.", errors[0].hint)

    @override_settings(
        SEARCH_INDEX_PUBLISHER_BACKEND="kafka",
        KAFKA_SERVER="localhost:9092",
        KAFKA_CHANNEL_CREATED_OR_UPDATED="my-topic",
        KAFKA_CHANNEL_DELETED="delete-topic",
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

        class MyPageModelWithoutAttr(Page):
            pass

        mock_get_page_models.return_value = [MyPageModelWithoutAttr]
        errors = check_search_index_content_type(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "search.E007")
        self.assertIn("does not define a 'search_index_content_type'", error.msg)
        self.assertIn("Either add an attribute/property 'search_index_content_type'", error.hint)

    @override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=("MyPageModelWithoutAttr",))
    @patch("cms.search.checks.get_page_models")
    def test_model_excluded_no_error(self, mock_get_page_models):
        """If a page model is listed in SEARCH_INDEX_EXCLUDED_PAGE_TYPES,
        we ignore it even if it doesn't define 'search_index_content_type'.
        """

        class MyPageModelWithoutAttr(Page):
            pass

        mock_get_page_models.return_value = [MyPageModelWithoutAttr]
        errors = check_search_index_content_type(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=())
    @patch("cms.search.checks.get_page_models")
    def test_model_with_content_type_no_error(self, mock_get_page_models):
        """If a page model defines a search_index_content_type, we should not get any errors."""

        class MyPageModelWithAttr(Page):
            search_index_content_type = "cms.search.my_page_model"

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
            pass  # no search_index_content_type

        class ExcludedPage(Page):
            pass  # no search_index_content_type but will be excluded

        mock_get_page_models.return_value = [IncludedPage, ExcludedPage]

        # Mark 'ExcludedPage' as excluded
        with override_settings(SEARCH_INDEX_EXCLUDED_PAGE_TYPES=("ExcludedPage",)):
            errors = check_search_index_content_type(app_configs=None)

        # We expect only 1 error from IncludedPage
        self.assertEqual(len(errors), 1)
        self.assertIn("IncludedPage", errors[0].msg)
        self.assertEqual(errors[0].id, "search.E007")
