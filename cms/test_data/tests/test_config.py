from django.test import SimpleTestCase
from pydantic import ValidationError

from cms.test_data.config import NonNegativeRangeConfig, RangeConfig, TestDataConfig


class TestDataConfigTestCase(SimpleTestCase):
    def test_default(self) -> None:
        TestDataConfig()
        TestDataConfig.model_validate({})

    def test_range_bounds(self) -> None:
        with self.assertRaises(ValidationError):
            RangeConfig(min=1, max=1)

        with self.assertRaises(ValidationError):
            RangeConfig(min=10, max=1)

    def test_range_rejects_zero_by_default(self):
        """A count of 0 images, datasets or revisions cannot be satisfied so should fail validation."""
        with self.assertRaises(ValidationError):
            RangeConfig(min=0, max=3)

        for config in [
            {"images": {"count": {"min": 0, "max": 3}}},
            {"datasets": {"count": {"min": 0, "max": 3}}},
            {"topics": {"count": {"min": 0, "max": 3}}},
        ]:
            with self.subTest(config), self.assertRaises(ValidationError):
                TestDataConfig.model_validate(config)

    def test_non_negative_range_allows_zero(self):
        NonNegativeRangeConfig(min=0, max=3)
        config = TestDataConfig.model_validate(
            {"topics": {"datasets": {"min": 0, "max": 1}, "explore_more": {"min": 0, "max": 2}}}
        )
        self.assertEqual(config.topics.datasets.min, 0)
        self.assertEqual(config.topics.explore_more.min, 0)

    def test_rejects_more_dataset_links_than_datasets(self):
        with self.assertRaises(ValidationError):
            TestDataConfig.model_validate({"datasets": {"count": 1}, "topics": {"datasets": 2}})

        # the minimum number of datasets must cover the most that can be linked
        with self.assertRaises(ValidationError):
            TestDataConfig.model_validate(
                {"datasets": {"count": {"min": 1, "max": 5}}, "topics": {"datasets": {"min": 1, "max": 2}}}
            )

        TestDataConfig.model_validate({"datasets": {"count": 2}, "topics": {"datasets": 2}})

    def test_rejects_too_many_dataset_blocks(self):
        with self.assertRaises(ValidationError):
            TestDataConfig.model_validate(
                {"datasets": {"count": 3}, "topics": {"datasets": 3, "dataset_manual_links": 1}}
            )

        # Should accept total of 3, which is current limit
        TestDataConfig.model_validate({"datasets": {"count": 3}, "topics": {"datasets": 2, "dataset_manual_links": 1}})
