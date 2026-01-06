import json
import re
from typing import TYPE_CHECKING
from unittest import TestCase

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from django.utils import translation

from cms.documents.models import CustomDocument

if TYPE_CHECKING:
    from wagtail.blocks import DeclarativeSubBlocksMetaclass, StructValue


class TranslationResetMixin:
    """Mixin that resets the translation state after each test.

    Use this mixin in test classes that access Welsh URLs or activate Welsh translations.
    Django's translation state is thread-local and can leak between tests when running
    in parallel, causing flaky test failures.

    Example:
        class MyTestCase(TranslationResetMixin, TestCase):
            def test_welsh_page(self):
                response = self.client.get("/cy")
                ...
    """

    def tearDown(self) -> None:  # pylint: disable=invalid-name
        translation.activate(settings.LANGUAGE_CODE)
        super().tearDown()  # type: ignore[misc]


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


class PanelBlockAssertions(SimpleTestCase):
    """Mixin that provides shared assertions for panel blocks."""

    def assertPanelBlockFields(  # pylint: disable=invalid-name
        self, value: "StructValue", expected_fields: set[str], block_class: "DeclarativeSubBlocksMetaclass"
    ) -> None:
        self.assertEqual(
            set(value.keys()),
            expected_fields,
            f"Unexpected fields in block value for {block_class.__name__}: {set(value.keys()) - expected_fields}",
        )
