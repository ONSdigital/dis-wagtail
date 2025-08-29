from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.core.utils import (
    get_client_ip,
    get_content_type_for_page,
    latex_formula_to_svg,
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
