from django.test import SimpleTestCase
from pydantic import ValidationError

from cms.test_data.config import RangeConfig, TestDataConfig


class TestDataConfigTestCase(SimpleTestCase):
    def test_default(self) -> None:
        TestDataConfig()
        TestDataConfig.model_validate({})

    def test_range_bounds(self) -> None:
        with self.assertRaises(ValidationError):
            RangeConfig(min=1, max=1)

        with self.assertRaises(ValidationError):
            RangeConfig(min=10, max=1)
