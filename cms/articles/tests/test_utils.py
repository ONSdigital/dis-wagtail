from django.test import TestCase

from cms.articles.utils import latex_formula_to_svg


class ArticlesUtilsTestCase(TestCase):
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
