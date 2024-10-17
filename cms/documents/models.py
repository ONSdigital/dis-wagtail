from wagtail.documents.models import AbstractDocument
from wagtail.documents.models import Document as WagtailDocument


class CustomDocument(AbstractDocument):
    admin_form_fields = WagtailDocument.admin_form_fields
