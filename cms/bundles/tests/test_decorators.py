from unittest.mock import MagicMock

from django.test import TestCase

from cms.bundles.decorators import ons_bundle_api_enabled


class OnsBundleApiEnabledDecoratorTest(TestCase):
    def test_decorator_runs_function_when_setting_is_true(self):
        """Verify the decorator executes the wrapped function when the setting is True."""
        # Create a mock function to act as our decorated function
        mock_func = MagicMock()
        mock_func.__name__ = "mock_func"

        decorated_func = ons_bundle_api_enabled(mock_func)

        with self.settings(DIS_DATASETS_BUNDLE_API_ENABLED=True):
            decorated_func("foo", kwarg1="bar")

        # Assert that our mock function was called exactly once with the correct arguments
        mock_func.assert_called_once_with("foo", kwarg1="bar")

    def test_decorator_skips_function_when_setting_is_false(self):
        """Verify the decorator does NOT execute the wrapped function when the setting is False."""
        # Create another mock function
        mock_func = MagicMock()
        mock_func.__name__ = "mock_func_api_disabled"

        decorated_func = ons_bundle_api_enabled(mock_func)

        with self.settings(DIS_DATASETS_BUNDLE_API_ENABLED=False):
            result = decorated_func("foo", kwarg1="bar")

        # Assert that our mock function was never called
        mock_func.assert_not_called()

        self.assertIsNone(result)
