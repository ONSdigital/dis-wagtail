from django.test import TestCase

from cms.core.templatetags.util_tags import extend


class ExtendFunctionTest(TestCase):
    """Tests of the `extend()` function.

    This isn't registered as a template tag, but made globally available to be used in
    Python code within Jinja2.
    """

    def test_append(self):
        """Test the original list is modified in place."""
        series = [{"name": "Series 1"}, {"name": "Series 2"}]
        series_item = {"name": "Series 3"}
        extend(series, series_item)
        self.assertEqual([{"name": "Series 1"}, {"name": "Series 2"}, {"name": "Series 3"}], series)

    def test_returns_none(self):
        """Test the return value of the filter.

        This is to ensure the same signature between this and the Nunjucks equivalent.
        """
        series = [{"name": "Series 1"}, {"name": "Series 2"}]
        series_item = {"name": "Series 3"}
        result = extend(series, series_item)
        self.assertIsNone(result)

    def test_bad_first_argument_type(self):
        """Test that an exception is raised if the first argument is not a list.

        This is likely to be called from a template macro, so we can't rely on
        annotations and tooling for type safety.
        """
        with self.assertRaises(TypeError):
            extend("not a list", {"name": "Series 3"})  # type: ignore
