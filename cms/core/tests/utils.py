import json
from unittest import TestCase

from bs4 import BeautifulSoup
from django.core.files.base import ContentFile

from cms.documents.models import CustomDocument


def get_test_document():
    """Creates a test document."""
    file = ContentFile("A boring example document", name="file.txt")
    return CustomDocument.objects.create(title="Test document", file=file)


def extract_response_jsonld(response_content: bytes, test_case: TestCase) -> dict[str, object]:
    """Extracts JSON-LD data from a HTTP response."""
    soup = BeautifulSoup(response_content, "html.parser")
    jsonld_scripts = soup.find_all("script", {"type": "application/ld+json"})
    test_case.assertEqual(len(jsonld_scripts), 1, "Expected exactly one JSON-LD script in the response.")
    return json.loads(jsonld_scripts[0].string)
