from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import RichTextBlock, URLBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page

from cms.core.blocks import (
    ONSEmbedBlock,
    RelatedLinksBlock,
    RelatedContentBlock,
)

#could use...
from cms.core.blocks.stream_blocks import CoreStoryBlock

from cms.core.fields import StreamField

class InformationPage(Page):

    template = "templates/pages/information_page.html"

    description = models.TextField(max_length=255)
    last_updated = models.DateField(blank=True, null=True)
    content = StreamField([
            ('heading', RichTextBlock()),
            ('paragraph', RichTextBlock()),
            ('image', ImageChooserBlock()),
            ('document', DocumentChooserBlock()),
            ('embed', ONSEmbedBlock()),
            ('related_links', RelatedLinksBlock(RelatedContentBlock())),
        ],
        blank=True,
        null=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('last_updated'),
        FieldPanel('content')
    ]
