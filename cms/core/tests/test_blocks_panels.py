from typing import ClassVar

from django.conf import settings
from django.test import TestCase
from wagtail.blocks import StructBlockValidationError

from cms.core.blocks.panels import (
    AnnouncementPanelBlock,
    BasePanelBlock,
    InformationPanelBlock,
    WarningPanelBlock,
)
from cms.core.tests.utils import PanelBlockAssertions


class PanelBlockTests(TestCase, PanelBlockAssertions):
    expected_panel_fields: ClassVar[set[str]] = {"body"}
    panel_block_classes: ClassVar[list[type]] = [WarningPanelBlock, AnnouncementPanelBlock, InformationPanelBlock]

    def test_base_panel_block_body_field_features(self):
        block = BasePanelBlock()
        self.assertPanelBlockFields(block.child_blocks, self.expected_panel_fields, BasePanelBlock)
        self.assertEqual(block.child_blocks["body"].features, settings.RICH_TEXT_BASIC)

    def test_panel_block_meta_attributes(self):
        blocks = [
            (WarningPanelBlock, "templates/components/streamfield/warning_panel.html", "warning", "Warning Panel"),
            (
                AnnouncementPanelBlock,
                "templates/components/streamfield/announcement_panel.html",
                "pick",
                "Announcement Panel",
            ),
            (
                InformationPanelBlock,
                "templates/components/streamfield/information_panel.html",
                "info-circle",
                "Information Panel",
            ),
        ]

        for block_class, template, icon, label in blocks:
            block = block_class()
            meta = block.meta

            self.assertEqual(meta.template, template)
            self.assertEqual(meta.icon, icon)
            self.assertEqual(meta.label, label)
            self.assertEqual(meta.group, "Panels")

    def test_panel_block_instantiation_and_validation(self):
        for block_class in self.panel_block_classes:
            block = block_class()
            value = block.to_python({"body": "<p>Test content</p>"})
            self.assertPanelBlockFields(value, self.expected_panel_fields, block_class)
            self.assertEqual(value["body"].source, "<p>Test content</p>")

    def test_panel_block_raises_validation_error_for_empty_body(self):
        for block_class in self.panel_block_classes:
            block = block_class()
            with self.assertRaises(StructBlockValidationError) as info:
                value = block.to_python({"body": ""})
                self.assertPanelBlockFields(value, self.expected_panel_fields, block_class)
                block.clean(value)
            self.assertEqual(info.exception.block_errors["body"].message, "This field is required.")

    def test_base_panel_block_is_abstract(self):
        self.assertTrue(BasePanelBlock._meta_class.abstract)  # pylint: disable=protected-access, no-member
