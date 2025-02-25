from django.forms import Media
from django.utils.functional import cached_property
from wagtail.blocks import StructBlock, TextBlock
from wagtail.blocks.struct_block import StructBlockAdapter
from wagtail.telepath import register


class TinyTableBlock(StructBlock):
    data = TextBlock(default="")

    class Meta:
        icon = "table"
        template = "tiny_table_block/table_block.html"


class TinyTableBlockAdapter(StructBlockAdapter):
    js_constructor = "streamblock.blocks.TinyTableBlockAdapter"

    @cached_property
    def media(self) -> Media:
        structblock_media = super().media
        js = [
            *structblock_media._js,  # pylint: disable=protected-access
            "tiny_table_block/js/vendor/tinymce/tinymce.min.js",
            "tiny_table_block/js/tiny-table-block.js",
        ]
        return Media(js=js)


register(TinyTableBlockAdapter(), TinyTableBlock)
