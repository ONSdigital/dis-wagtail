from collections.abc import MutableSequence
from typing import TYPE_CHECKING, Any

from wagtail.blocks import ListBlock
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.templatetags.wagtailcore_tags import richtext

from cms.core.models import Definition

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue, StructValue


class DefinitionsBlock(ListBlock):
    def __init__(self, search_index: bool = True, **kwargs: Any) -> None:
        super().__init__(SnippetChooserBlock(Definition), search_index=search_index, **kwargs)

    class Meta:
        template = "templates/components/streamfield/definitions_block.html"

    def get_context(self, value: "StreamValue", parent_context: dict | None = None) -> dict:
        """Inject formatted definitions to be used with ONS Accordion component."""
        context: dict = super().get_context(value, parent_context)
        context["formatted_definitions"] = [
            {
                "headingLevel": 3,
                "title": definition.name,
                "content": richtext(definition.definition),
            }
            for definition in value
        ]
        return context

    def clean(self, value: "StructValue") -> MutableSequence:
        """Deduplicate the definitions."""
        result: MutableSequence = super().clean(value)

        seen = set()
        for term in result:
            if term in seen:
                result.remove(term)
            else:
                seen.add(term)

        return result
