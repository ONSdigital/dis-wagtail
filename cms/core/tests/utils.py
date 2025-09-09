import json
import re
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


def extract_datalayer_pushed_values(html_content: str) -> dict[str, object]:
    """Extracts all json arguments to `datalayer.push()` calls from the HTML content and returns them all their values,
    unified in a single dictionary.
    """
    datalayer_push_pattern = r"dataLayer\.push\s*\(\s*({.*?})\s*\)"
    datalayer_push_args = re.findall(datalayer_push_pattern, html_content, re.DOTALL)
    datalayer_values: dict[str, object] = {}
    for datalayer_arg in datalayer_push_args:
        arg_values = json.loads(datalayer_arg)
        datalayer_values.update(arg_values)
    return datalayer_values
