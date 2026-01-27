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

## "Too many open files" Error on macOS

### Problem

When running tests or development servers on macOS, you may encounter a "Too many open files" error. This is due to the default limit on the number of file descriptors that can be opened simultaneously.

### Symptoms

- Errors during test execution or server startup
- Error message: "OSError: [Errno 24] Too many open files"

### Solution

Increase the file descriptor limit on your macOS system by following these steps:

1. Open a terminal window.
2. Check the current limit with the command:
    ```bash
    ulimit -n
    ```
3. Increase the limit by adding the following lines to your shell configuration file (e.g.,
   `~/.bash_profile`, `~/.zshrc`):
    ```bash
    ulimit -n 65536
    ```
4. Apply the changes by running:
    ```bash
    source ~/.bash_profile  # or source ~/.zshrc
    ```
5. Verify the new limit with:
    ```bash
    ulimit -n
    ```

If the above doesn't work, you may need to run the following command:

```bash
sudo launchctl limit maxfiles 65536 200000
```

This sets both the soft and hard limits for file descriptors using `launchctl`.

### When to Apply This Fix

- When `ulimit -n` returns a low number (e.g., 256 or 1024)
- When encountering "Too many open files" errors during development or testing on macOS
