from django.db.models import DateField
from openpyxl.drawing.text import TextField
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import RichTextBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page

from cms.core.blocks import ONSEmbedBlock, RelatedLinksBlock
from cms.core.fields import StreamField


class InformationPage(Page):

    description = TextField(max_lenth=255)
    last_updated = DateField(blank=True)
    content = StreamField(
        [
            ('Heading', RichTextBlock()),
            ('Paragraph', RichTextBlock()),
            ('Image', ImageChooserBlock()),
            ('Document', DocumentChooserBlock()),
            ('Embed', ONSEmbedBlock()),#ONSEmbedBlock
            ('Related_links', RelatedLinksBlock()),
        ]
    )

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('last_updated'),
        FieldPanel('content')
    ]
