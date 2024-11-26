from wagtail.documents.models import AbstractDocument

from cms.private_media.models import PrivateDocumentMixin


class CustomDocument(PrivateDocumentMixin, AbstractDocument):
    """Custom Wagtail document class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """
    pass
