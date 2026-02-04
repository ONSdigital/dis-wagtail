from unittest.mock import MagicMock, patch

from django.core.checks import Error
from django.test import TestCase
from wagtail.contrib.settings.models import (
    BaseGenericSetting as WagtailBaseGenericSetting,
)
from wagtail.contrib.settings.models import (
    BaseSiteSetting as WagtailBaseSiteSetting,
)
from wagtail.models import Page

from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.checks import check_wagtail_pages, check_wagtail_settings
from cms.core.fields import StreamField
from cms.core.forms import PageWithEquationsAdminForm
from cms.core.models.base import BaseGenericSetting, BaseSiteSetting


class CheckWagtailSettingsTests(TestCase):
    """Tests for check_wagtail_settings which validates that settings models extend project base classes."""

    @patch("cms.core.checks.apps.get_models")
    def test_site_setting_not_extending_base_raises_error(self, mock_get_models):
        """Site settings that don't extend BaseSiteSetting should raise an error."""

        class BadSiteSetting(WagtailBaseSiteSetting):
            class Meta:
                abstract = True

        mock_get_models.return_value = [BadSiteSetting]
        errors = list(check_wagtail_settings())

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Error)
        self.assertIn("Site setting does not extend project base", errors[0].msg)
        self.assertIn("BaseSiteSetting", errors[0].hint)

    @patch("cms.core.checks.apps.get_models")
    def test_generic_setting_not_extending_base_raises_error(self, mock_get_models):
        """Generic settings that don't extend BaseGenericSetting should raise an error."""

        class BadGenericSetting(WagtailBaseGenericSetting):
            class Meta:
                abstract = True

        mock_get_models.return_value = [BadGenericSetting]
        errors = list(check_wagtail_settings())

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Error)
        self.assertIn("Generic setting does not extend project base", errors[0].msg)
        self.assertIn("BaseGenericSetting", errors[0].hint)

    @patch("cms.core.checks.apps.get_models")
    def test_site_setting_extending_base_no_error(self, mock_get_models):
        """Site settings that properly extend BaseSiteSetting should not raise errors."""

        class GoodSiteSetting(BaseSiteSetting):
            class Meta:
                abstract = True

        mock_get_models.return_value = [GoodSiteSetting]
        errors = list(check_wagtail_settings())

        self.assertEqual(errors, [])

    @patch("cms.core.checks.apps.get_models")
    def test_generic_setting_extending_base_no_error(self, mock_get_models):
        """Generic settings that properly extend BaseGenericSetting should not raise errors."""

        class GoodGenericSetting(BaseGenericSetting):
            class Meta:
                abstract = True

        mock_get_models.return_value = [GoodGenericSetting]
        errors = list(check_wagtail_settings())

        self.assertEqual(errors, [])

    @patch("cms.core.checks.apps.get_models")
    def test_unrelated_model_no_error(self, mock_get_models):
        """Models that aren't Wagtail settings should not raise errors."""

        class UnrelatedModel:
            class Meta:
                abstract = True

        mock_get_models.return_value = [UnrelatedModel]
        errors = list(check_wagtail_settings())

        self.assertEqual(errors, [])


class CheckWagtailPagesTests(TestCase):
    """Tests for check_wagtail_pages which validates page models using SectionStoryBlock."""

    @patch("cms.core.checks.get_page_models")
    def test_page_with_section_story_block_without_correct_form_raises_error(self, mock_get_page_models):
        """Pages using SectionStoryBlock without PageWithEquationsAdminForm should raise an error."""
        mock_field = MagicMock(spec=StreamField)
        mock_field.block_types_arg = MagicMock(spec=SectionStoryBlock)

        class BadPageModel(Page):
            class Meta:
                abstract = True

        BadPageModel._meta.get_fields = MagicMock(return_value=[mock_field])

        mock_get_page_models.return_value = [BadPageModel]
        errors = list(check_wagtail_pages())

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Error)
        self.assertIn("does not use the correct base form class", errors[0].msg)
        self.assertIn("PageWithEquationsAdminForm", errors[0].hint)

    @patch("cms.core.checks.get_page_models")
    def test_page_with_section_story_block_with_correct_form_no_error(self, mock_get_page_models):
        """Pages using SectionStoryBlock with PageWithEquationsAdminForm should not raise errors."""
        mock_field = MagicMock(spec=StreamField)
        mock_field.block_types_arg = MagicMock(spec=SectionStoryBlock)

        class GoodPageModel(Page):
            base_form_class = PageWithEquationsAdminForm

            class Meta:
                abstract = True

        GoodPageModel._meta.get_fields = MagicMock(return_value=[mock_field])

        mock_get_page_models.return_value = [GoodPageModel]
        errors = list(check_wagtail_pages())

        self.assertEqual(errors, [])

    @patch("cms.core.checks.get_page_models")
    def test_page_without_stream_field_no_error(self, mock_get_page_models):
        """Pages without StreamField should not raise errors."""
        mock_field = MagicMock()  # Not a StreamField

        class RegularPageModel(Page):
            class Meta:
                abstract = True

        RegularPageModel._meta.get_fields = MagicMock(return_value=[mock_field])

        mock_get_page_models.return_value = [RegularPageModel]
        errors = list(check_wagtail_pages())

        self.assertEqual(errors, [])

    @patch("cms.core.checks.get_page_models")
    def test_page_with_stream_field_without_section_story_block_no_error(self, mock_get_page_models):
        """Pages with StreamField but not SectionStoryBlock should not raise errors."""
        mock_field = MagicMock(spec=StreamField)
        mock_field.block_types_arg = MagicMock()  # Not a SectionStoryBlock

        class PageWithOtherStreamField(Page):
            class Meta:
                abstract = True

        PageWithOtherStreamField._meta.get_fields = MagicMock(return_value=[mock_field])

        mock_get_page_models.return_value = [PageWithOtherStreamField]
        errors = list(check_wagtail_pages())

        self.assertEqual(errors, [])
