from django.utils.translation import gettext_lazy as _
from wagtail.blocks import CharBlock, PageChooserBlock, StreamBlock, StructBlock, URLBlock
from wagtail.images.blocks import ImageChooserBlock


class ExploreMoreExternalLinkBlock(StructBlock):
    url = URLBlock(label=_("External URL"))
    title = CharBlock()
    description = CharBlock()
    thumbnail = ImageChooserBlock()

    class Meta:
        icon = "link"


class ExploreMoreInternalLinkBlock(StructBlock):
    page = PageChooserBlock()
    title = CharBlock(required=False, help_text=_("Use to override the chosen page title."))
    description = CharBlock(
        required=False,
        help_text=_(
            "Use to override the chosen page description. "
            "By default, we will attempt to use the listing summary or the summary field."
        ),
    )
    thumbnail = ImageChooserBlock(required=False, help_text=_("Use to override the chosen page listing image."))

    class Meta:
        icon = "doc-empty-inverse"


class ExploreMoreStoryBlock(StreamBlock):
    external_link = ExploreMoreExternalLinkBlock()
    internal_link = ExploreMoreInternalLinkBlock()
