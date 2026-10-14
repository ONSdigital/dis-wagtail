from django import forms
from django.forms import Media
from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtail_polymath.blocks import MathBlock as PolymathMathBlock
from wagtail_polymath.widgets import PolymathTextareaWidget


class MathJaxConfigTextareaWidget(PolymathTextareaWidget):
    @property
    def media(self) -> Media:
        # The config script must come after polymath's widget script, which sets window.MathJax.
        # A single list keeps that order when Django merges media.
        widget_media = super().media
        return Media(js=[*widget_media._js, "js/mathjax-config.js"], css=widget_media._css)  # pylint: disable=protected-access


class MathBlock(PolymathMathBlock):
    @cached_property
    def field(self) -> forms.CharField:
        field_kwargs = {"widget": MathJaxConfigTextareaWidget(attrs={"rows": self.rows})}
        field_kwargs.update(self.field_options)
        return forms.CharField(**field_kwargs)


class EquationBlock(blocks.StructBlock):
    equation = MathBlock(
        label="Mathematical equation",
        help_text="Enter a mathematical equation using the MathJax syntax such as"
        " <code>$$\\frac{(n^2+n)(2n+1)}{6}$$</code>.",
        required_on_save=True,
    )
    svg = blocks.TextBlock(required=False)

    class Meta:
        icon = "openquote"
        template = "templates/components/streamfield/equation_block.html"


class EquationBlockAdapter(StructBlockAdapter):
    js_constructor = "cms.core.blocks.equation.EquationBlock"

    @cached_property
    def media(self) -> Media:
        structblock_media = super().media
        return Media(js=[*structblock_media._js, "js/blocks/equation-block.js"], css=structblock_media._css)  # pylint: disable=protected-access


register(EquationBlockAdapter(), EquationBlock)
