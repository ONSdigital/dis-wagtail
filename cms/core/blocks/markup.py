from django.utils.text import slugify
from wagtail import blocks


class HeadingBlock(blocks.CharBlock):
    class Meta:
        icon = "title"
        form_classname = "title"
        template = "templates/components/streamfield/heading_block.html"
        label = "Section heading"

    def __init__(self, **kwargs):
        self.show_back_to_toc = kwargs.pop("show_back_to_toc", False)
        kwargs.setdefault("help_text", "This is output as level 2 heading (<code>h2</code>)")

        super().__init__(**kwargs)

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        context["show_back_to_toc"] = self.show_back_to_toc

        return context

    def to_table_of_contents_items(self, value):
        return [{"url": "#" + slugify(value), "text": value}]


class QuoteBlock(blocks.StructBlock):
    quote = blocks.CharBlock(form_classname="title")
    attribution = blocks.CharBlock(required=False)

    class Meta:
        icon = "openquote"
        template = "templates/components/streamfield/quote_block.html"