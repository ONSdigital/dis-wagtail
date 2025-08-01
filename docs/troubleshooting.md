# Troubleshooting Guide

This guide contains solutions to common development issues encountered in the ONS Wagtail CMS project. Each section provides context about the problem, symptoms to look for, and tested solutions.

## Test Locale Contamination

### Problem
When writing tests that access content in different languages or work with Django's translation system, tests can contaminate each other by leaving the active language changed from the default. This can cause subsequent tests to fail unexpectedly.

### Symptoms
- Tests pass when run individually but fail when run as part of a test suite
- Tests fail intermittently depending on the order they're executed
- Error messages appear in unexpected languages
- Content appears in wrong language during test execution

### Solution
Add a `tearDown()` method to your test class that resets the translation to the default language:

```python
from django.conf import settings
from django.utils import translation

class YourTestClass(TestCase):
    def tearDown(self):
        # Reset the translation to the default language after each test to avoid
        # test contamination issues.
        translation.activate(settings.LANGUAGE_CODE)
        return super().tearDown()
```

### When to Apply This Fix
- Tests that work with multi-language content
- Tests that interact with Wagtail's `Locale` model
- Any test class where locale-related test failures occur

### Examples
This pattern has been applied to:
- `cms/articles/tests/test_pages.py` - `StatisticalArticlePageTests`
- `cms/core/tests/test_pages.py` - `HomePageTests`, `PageCanonicalUrlTests`, `ErrorPageTests`
