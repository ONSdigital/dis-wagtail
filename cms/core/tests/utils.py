from django.core.files.base import ContentFile

from cms.documents.models import CustomDocument


def get_test_document():
    """Creates a test document."""
    file = ContentFile("A boring example document", name="file.txt")
    return CustomDocument.objects.create(title="Test document", file=file)
