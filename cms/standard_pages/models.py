from django.db import models
from django.db.models import DateField
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import RichTextBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page

from cms.core.blocks import ONSEmbedBlock, RelatedLinksBlock
from cms.core.fields import StreamField


class InformationPage(Page):

    description = models.CharField(max_length=255)
    last_updated = models.DateField(blank=True, null=True)
    content = StreamField(
        [
            ('heading', RichTextBlock()),
            ('paragraph', RichTextBlock()),
            ('image', ImageChooserBlock()),
            ('document', DocumentChooserBlock()),
            ('embed', ONSEmbedBlock()),
            ('related_links', RelatedLinksBlock()),
        ],
        blank=True,
        null=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('last_updated'),
        FieldPanel('content')
    ]
