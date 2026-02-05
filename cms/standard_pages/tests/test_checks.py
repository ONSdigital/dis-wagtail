from unittest.mock import patch

from django.test import TestCase

from cms.standard_pages.checks import check_wagtail_pages
from cms.standard_pages.section_blocks import CoreStoryBlock


class CheckStandardPagesTests(TestCase):
    """Tests for check_standard_pages system check."""

    @patch("cms.standard_pages.checks.check_page_models_for_story_block")
    def test_delegates_to_helper_with_core_story_block(self, mock_helper):
        """check_standard_pages should call the helper with CoreStoryBlock."""
        mock_helper.return_value = iter([])

        list(check_wagtail_pages())

        mock_helper.assert_called_once_with(CoreStoryBlock)
