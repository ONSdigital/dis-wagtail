from typing import Any

from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock


class PointAnnotationStructValue(StructValue):
    def get_config(self) -> dict[str, Any]:
        if label_offset_y := self.get("label_offset_y"):
            # The SVG coordinate system measures from the top left. It makes more sense
            # to users to measure from the bottom left, to match the chart coordinates.
            label_offset_y = -label_offset_y
        return {
            "text": self.get("label"),
            "point": {
                # The Design System component expects 0-based indices.
                "x": self.get("x_position") - 1,
                "y": self.get("y_position"),
            },
            "labelOffsetX": self.get("label_offset_x"),
            "labelOffsetY": label_offset_y,
        }


class PointAnnotationBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)

    x_position = TextInputIntegerBlock(
        label="Data point number",
        required=True,
    )
    y_position = TextInputFloatBlock(
        label="Value",
        required=True,
        help_text="The label will point to this location on the value axis.",
    )

    label_offsets = blocks.StaticBlock(admin_text="Offsets are measured in pixels")
    label_offset_x = TextInputIntegerBlock(label="Offset X", required=False)
    label_offset_y = TextInputIntegerBlock(label="Offset Y", required=False)

    class Meta:
        value_class = PointAnnotationStructValue
