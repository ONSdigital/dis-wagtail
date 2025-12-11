from django.forms import Media
from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtailmath.blocks import MathBlock


class EquationBlock(blocks.StructBlock):
    equation = MathBlock(label="Mathematical equation")
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
