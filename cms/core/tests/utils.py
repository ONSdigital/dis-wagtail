import json
import re
import sys
from unittest import TestCase

from bs4 import BeautifulSoup
from django.conf import settings
from django.conf.urls.i18n import is_language_prefix_patterns_used
from django.core.files.base import ContentFile
from django.urls import clear_url_caches

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


def reset_url_caches():
    # Make sure the cache is empty before we are doing our tests.
    clear_url_caches()
    # Force reload of URLconf module to re-evaluate i18n_patterns
    root_urlconf = getattr(settings, "ROOT_URLCONF", None)
    if root_urlconf and root_urlconf in sys.modules:
        del sys.modules[root_urlconf]
        # Also delete any submodules
        modules_to_delete = [mod for mod in sys.modules if mod.startswith(root_urlconf + ".")]
        for mod in modules_to_delete:
            del sys.modules[mod]

    is_language_prefix_patterns_used.cache_clear()
