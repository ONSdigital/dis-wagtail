import urllib.parse
from unittest.mock import Mock

from django.http import HttpRequest, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.core.blocks.embeddable import ImageBlock
from cms.core.utils import (
    get_client_ip,
    get_content_type_for_page,
    latex_formula_to_svg,
    redirect,
    redirect_to_parent_listing,
)
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.topics.tests.factories import TopicPageFactory


class ClientIPTestCase(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.factory = RequestFactory()

    def test_get_client_ip(self) -> None:
        request = self.factory.get("/")
        self.assertEqual(get_client_ip(request), "127.0.0.1")

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_cannot_get_client_ip_in_external_env(self) -> None:
        request = self.factory.get("/")

        with self.assertRaisesMessage(RuntimeError, "Cannot get client IP in external environment."):
            get_client_ip(request)


class LatexFormulaTestCase(TestCase):
    def test_latex_formula_to_svg_simple_formula(self):
        """Test the conversion of LaTeX formula to SVG."""
        # Test with a simple LaTeX formula
        latex_formula = r"\frac{a}{b}"
        result = latex_formula_to_svg(latex_formula)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("</g>", result)
        self.assertTrue(result.endswith("</svg>\n"))

    def test_latex_formula_to_svg_complex_formula(self):
        """Test the conversion of a more complex LaTeX formula to SVG."""
        # Test with a more complex LaTeX formula
        latex_formula = r"{{(^B \,Oct\,(T - 1)\, + \,^B \,Nov\,(T\, + \,2)\,)} \over 4}\, + \,{{3\,*\,(^B \,Nov\,(T - 1)\, + \,^B \,Oct\,(T\, + \,2)\,)} \over 4}\, + \sum\limits_{i = Dec\,\,(T - 1)}^{i = Sep\,\,(T + 2)} {B_i }"  # noqa: E501 pylint: disable=line-too-long
        result = latex_formula_to_svg(latex_formula)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("</g>", result)
        self.assertTrue(result.endswith("</svg>\n"))

    def test_latex_formula_to_svg_formula_with_background(self):
        """Test the conversion of a LaTeX formula to SVG with a background."""
        # Test with a LaTeX formula with a background
        latex_formula = r"\frac{a}{b}"
        result = latex_formula_to_svg(latex_formula, transparent=False)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("fill: #ffffff", result)

        result = latex_formula_to_svg(latex_formula, transparent=True)
        self.assertTrue(result.startswith("<svg"))
        self.assertNotIn("fill: #ffffff", result)

    def test_latex_formula_to_svg_with_advanced_mathematical_symbols(self):
        latex_formula = (
            r"\begin{bmatrix}"
            r"{a_{11}}&{a_{12}}&{\cdots}&{a_{1n}}\\"
            r"{a_{21}}&{a_{22}}&{\cdots}&{a_{2n}}\\"
            r"{\vdots}&{\vdots}&{\ddots}&{\vdots}\\"
            r"{a_{m1}}&{a_{m2}}&{\cdots}&{a_{mn}}\\"
            r"\end{bmatrix}"
        )
        result = latex_formula_to_svg(latex_formula)
        self.assertTrue(result.startswith("<svg"))
        self.assertIn("</g>", result)
        self.assertTrue(result.endswith("</svg>\n"))

    def test_latex_formula_to_svg_empty_formula(self):
        """Test the conversion of an empty LaTeX formula to SVG."""
        # Test with an empty LaTeX formula
        latex_formula = ""
        with self.assertRaises(RuntimeError):
            latex_formula_to_svg(latex_formula)

    def test_latex_formula_to_svg_invalid_formula(self):
        """Test the conversion of an invalid LaTeX formula to SVG."""
        # Test with an invalid LaTeX formula
        latex_formula = r"\frac{a}{b"
        with self.assertRaises(RuntimeError):
            latex_formula_to_svg(latex_formula)


class TestContentTypeForPage(TestCase):
    def test_get_content_type_for_page(self):
        """Test the content type for a given page."""
        # Create a dummy page
        page = StatisticalArticlePageFactory(title="Test Article")
        content_type = get_content_type_for_page(page)
        self.assertEqual(content_type, "Article")

        page = TopicPageFactory(title="Test Topic")
        content_type = get_content_type_for_page(page)
        self.assertEqual(content_type, "Topic")

        page = MethodologyPageFactory(title="Test Methodology")
        content_type = get_content_type_for_page(page)
        self.assertEqual(content_type, "Methodology")


class RedirectToParentListingTestCase(SimpleTestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.parent = Mock(spec_set=["get_url", "get_articles_search_url"])
        self.page = Mock()
        self.page.get_parent.return_value.specific_deferred = self.parent

    def test_redirects_to_root_if_no_parent(self):
        self.page.get_parent.return_value = None
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="get_articles_search_url"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, "/")

    def test_redirects_to_listing_url_if_method_exists_and_returns_url(self):
        self.parent.get_articles_search_url = Mock(return_value="/articles/search/")
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="get_articles_search_url"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.url, "/articles/search/")

    def test_redirects_to_parent_url_if_listing_method_missing(self):
        self.parent.get_url = Mock(return_value="/parent/")
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="nonexistent_method"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, "/parent/")

    def test_redirects_to_parent_url_if_listing_method_returns_none(self):
        self.parent.get_articles_search_url = Mock(return_value=None)
        self.parent.get_url = Mock(return_value="/parent/")
        response = redirect_to_parent_listing(
            page=self.page, request=self.request, listing_url_method_name="get_articles_search_url"
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, "/parent/")


class RedirectUtilityTestCase(SimpleTestCase):
    def test_temporary_redirect_default(self):
        response = redirect("/foo")
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.url, "/foo")

    def test_temporary_redirect_preserve_request_false(self):
        response = redirect("/bar", preserve_request=False)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/bar")

    def test_permanent_redirect_preserve_request_false(self):
        response = redirect("/baz", permanent=True, preserve_request=False)
        self.assertIsInstance(response, HttpResponsePermanentRedirect)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/baz")

    def test_permanent_redirect_preserve_request_true(self):
        response = redirect("/qux", permanent=True, preserve_request=True)
        self.assertIsInstance(response, HttpResponsePermanentRedirect)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/qux")

    def test_temporary_redirect_preserve_request_true(self):
        response = redirect("/quux", preserve_request=True)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.url, "/quux")

    def test_args_are_passed(self):
        # HttpResponseRedirect only uses the first positional argument (the URL)
        response = redirect("/args-test", "unused-arg")
        self.assertEqual(response.url, "/args-test")

    def test_unicode_url(self):
        response = redirect("/unicodé")
        expected_url = urllib.parse.quote("/unicodé", safe="/:")
        self.assertEqual(response.url, expected_url)


class ImageBlockToKbTest(SimpleTestCase):
    def setUp(self) -> None:
        self.block = ImageBlock()

    def test_to_kb_none_returns_none(self) -> None:
        self.assertIsNone(self.block.to_kb(None))

    def test_to_kb_values_up_to_512_bytes_return_1kb(self) -> None:
        self.assertEqual(self.block.to_kb(0), 1)
        self.assertEqual(self.block.to_kb(1), 1)
        self.assertEqual(self.block.to_kb(511), 1)
        self.assertEqual(self.block.to_kb(512), 1)

    def test_to_kb_rounding_above_half_kb(self) -> None:
        # 513 bytes (~0.501 KB) rounds to 1
        self.assertEqual(self.block.to_kb(513), 1)
        # 1024 bytes -> 1 KB
        self.assertEqual(self.block.to_kb(1024), 1)
        # 1536 bytes -> 1.5 KB -> 2 KB under Python rounding
        self.assertEqual(self.block.to_kb(1536), 2)
