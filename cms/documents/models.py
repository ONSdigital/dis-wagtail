from collections.abc import Sequence
from typing import ClassVar

from wagtail.documents.models import AbstractDocument, Document

from cms.private_media.models import PrivateDocumentMixin


class CustomDocument(PrivateDocumentMixin, AbstractDocument):
    """Custom Wagtail document class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """

    admin_form_fields: ClassVar[Sequence[str]] = Document.admin_form_fields
