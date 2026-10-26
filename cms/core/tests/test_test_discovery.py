from pathlib import Path

from django.test import SimpleTestCase

CMS_ROOT = Path(__file__).resolve().parents[2]


class TestDiscoveryTestCase(SimpleTestCase):
    def test_every_test_module_is_in_a_package(self):
        """Test discovery skips any directory without an __init__.py, so tests inside it never run.

        This walks every test module under cms/ and fails if any ancestor directory up to cms/ is not a package.
        """
        missing = set()
        for test_module in CMS_ROOT.rglob("test*.py"):
            directory = test_module.parent
            while directory != CMS_ROOT.parent:
                if not (directory / "__init__.py").exists():
                    missing.add(str(directory.relative_to(CMS_ROOT.parent)))
                    break
                directory = directory.parent

        self.assertEqual(sorted(missing), [], "These directories need an __init__.py or their tests are never run")
