from wagtail.documents.models import AbstractDocument
from wagtail.documents.models import Document as WagtailDocument


class CustomDocument(AbstractDocument):
    """Custom Wagtail document class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """

    admin_form_fields = WagtailDocument.admin_form_fields
