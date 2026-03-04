import json
import subprocess
import sys
import threading
from copy import deepcopy
from io import StringIO

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


class ThreadingExceptHookTestCase(SimpleTestCase):
    @staticmethod
    def _raise_module_not_found_error():
        import not_a_module  # noqa: F401 py  # pylint: disable=import-outside-toplevel,import-error,unused-import

    @staticmethod
    def _raise_import_error():
        from cms import (  # pylint: disable=import-outside-toplevel,no-name-in-module,unused-import
            not_a_module,  # noqa: F401
        )

    @classmethod
    def _raise_recursion_error(cls):
        cls._raise_recursion_error()

    def setUp(self):
        self.log_stream = StringIO()

        # cms.settings.test sets the logging handler to null, so reset it to stream so we can capture it
        custom_logging = deepcopy(settings.LOGGING)
        custom_logging["handlers"]["console"]["class"] = "logging.StreamHandler"
        custom_logging["handlers"]["console"]["stream"] = self.log_stream
        self.enterContext(self.settings(LOGGING=custom_logging))

    def test_is_configured(self):
        self.assertIs(threading.excepthook, excepthook.threading_except_hook)

    def test_unhandled_exceptions(self):
        for func, exception_class in [
            (lambda: 1 / 0, ZeroDivisionError),
            (lambda: 10.0**1000, OverflowError),
            (self._raise_module_not_found_error, ModuleNotFoundError),
            (self._raise_import_error, ImportError),
            (self._raise_recursion_error, RecursionError),
        ]:
            self.log_stream.seek(0)

            with self.subTest(exception_class.__name__):
                thread = threading.Thread(target=func)
                thread.start()
                thread.join()

                # If it looks like JSON, it's probably the JSON formatter
                log_message = json.loads(self.log_stream.getvalue())

                self.assertEqual(log_message["namespace"], excepthook.logger.name)
                self.assertEqual(log_message["event"], "Unhandled exception in thread")
                self.assertEqual(log_message["data"], {"native_thread_id": thread.native_id, "thread_id": thread.ident})
                self.assertIn(exception_class.__name__, log_message["errors"][0]["message"])
