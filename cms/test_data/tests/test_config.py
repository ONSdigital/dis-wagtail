from django.test import SimpleTestCase
from faker import Faker
from pydantic import ValidationError

from cms.test_data.config import RangeConfig, TestDataConfig, get_count


class TestDataConfigTestCase(SimpleTestCase):
    def test_default(self) -> None:
        TestDataConfig()
        TestDataConfig.model_validate({})

    def test_count(self) -> None:
        self.assertEqual(get_count(1, Faker()), 1)

        for _ in range(100):
            self.assertLessEqual(get_count(RangeConfig(min=1, max=10), Faker()), 10)
            self.assertGreaterEqual(get_count(RangeConfig(min=1, max=10), Faker()), 1)

    def test_range_bounds(self) -> None:
        with self.assertRaises(ValidationError):
            RangeConfig(min=1, max=1)

        with self.assertRaises(ValidationError):
            RangeConfig(min=10, max=1)
