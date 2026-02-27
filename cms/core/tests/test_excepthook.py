import json
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase

from cms.core import excepthook


class ExceptHookTestCase(SimpleTestCase):
    def test_is_configured(self):
        self.assertIs(sys.excepthook, excepthook.except_hook)

    def _run_code(self, code: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            args=[sys.executable, str(settings.BASE_DIR / "manage.py"), "shell", "-c", code],
            check=False,
            text=True,
            cwd=settings.BASE_DIR,
            capture_output=True,
            env={"DJANGO_SETTINGS_MODULE": "cms.settings.production"},
        )

    def test_unhandled_exceptions(self):
        for code, exception_class in [
            ("1 / 0", ZeroDivisionError),
            ("import not_a_module", ModuleNotFoundError),
            ("from cms import not_a_module", ImportError),
            ("10.0 ** 1000", OverflowError),
            ("r = lambda: r(); r()", RecursionError),
        ]:
            with self.subTest(code):
                process = self._run_code(code)
                self.assertEqual(process.returncode, 1)

                log_message = json.loads(process.stderr)
                self.assertEqual(log_message["namespace"], excepthook.logger.name)
                self.assertEqual(log_message["event"], "Unhandled exception")
                self.assertIn(exception_class.__name__, log_message["errors"][0]["message"])

    def test_syntax_error(self):
        process = self._run_code("syntax error")

        self.assertEqual(process.returncode, 1)
        self.assertIn("SyntaxError: invalid syntax", process.stderr)

        # The output should not be JSON
        with self.assertRaises(ValueError):
            json.loads(process.stderr)
