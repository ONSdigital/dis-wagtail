import io

import matplotlib as mpl
import matplotlib.pyplot as plt

FORMULA_INDICATOR = "$$"

# Use LaTeX to render text in matplotlib
mpl.rcParams.update({"text.usetex": True})


def latex_formula_to_svg(latex: str, *, fontsize: int = 16, transparent: bool = True) -> str:
    """Generates an SVG string from a LaTeX expression.

    Args:
        latex (str): The LaTeX string to render.
        fontsize (int, optional): The font size for the LaTeX output. Defaults to 16.
        transparent (bool, optional): If True, the SVG will have a transparent background. Defaults to True.

    Returns:
        str: A string containing the SVG representation of the LaTeX expression.
    """
    fig = plt.figure()
    svg_buffer = io.StringIO()
    try:
        fig.text(0, 0, rf"${latex}$", fontsize=fontsize)
        fig.savefig(svg_buffer, format="svg", bbox_inches="tight", transparent=transparent)
        svg_string = svg_buffer.getvalue()
    finally:
        plt.close(fig)
        svg_buffer.close()

    # Remove first 3 lines of the SVG string
    svg_string = "\n".join(svg_string.split("\n")[3:])

    return svg_string
