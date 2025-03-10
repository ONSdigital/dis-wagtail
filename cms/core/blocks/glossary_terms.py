from typing import TYPE_CHECKING

from django.utils.text import slugify
from wagtail.blocks import ListBlock, StructBlock
from wagtail.snippets.blocks import SnippetChooserBlock

from cms.core.models import GlossaryTerm

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue, StructValue


class GlossaryTermsBlock(StructBlock):
    content = ListBlock(SnippetChooserBlock(GlossaryTerm))

    class Meta:
        template = "templates/components/streamfield/glossary_section_block.html"

    def to_table_of_contents_items(self, value: "StructValue") -> list[dict[str, str]]:
        """Convert the value to the table of contents component macro format."""
        return [{"url": "#" + slugify(value["title"]), "text": value["title"]}]

    def get_context(self, value: "StreamValue", parent_context: dict | None = None) -> dict:
        """Inject formatted glossary terms to be used with ONS Accordion component."""
        context: dict = super().get_context(value, parent_context)
        context["formatted_glossary_terms"] = [
            {
                "title": glossary_term.name,
                "content": glossary_term.definition,
            }
            for glossary_term in value["content"]
        ]
        return context
