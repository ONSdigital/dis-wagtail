from typing import Any, cast

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
                "x": self.get_x_position(),
                "y": self.get("y_position"),
            },
            "labelOffsetX": self.get("label_offset_x"),
            "labelOffsetY": label_offset_y,
        }

    def get_x_position(self) -> float:
        raise NotImplementedError("Subclasses must implement get_x_position()")


class BasePointAnnotationBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)
    x_position = blocks.StaticBlock()
    y_position = blocks.StaticBlock()
    label_offsets = blocks.StaticBlock(admin_text="Offsets are measured in pixels")
    label_offset_x = TextInputIntegerBlock(label="Offset X", required=False)
    label_offset_y = TextInputIntegerBlock(label="Offset Y", required=False)


class CategoryPointAnnotationStructValue(PointAnnotationStructValue):
    def get_x_position(self) -> int:
        # The Design System component expects 0-based indices.
        return cast(int, self.get("x_position")) - 1


class CategoryPointAnnotationBlock(BasePointAnnotationBlock):
    """Point annotation for when the x-axis is discrete/categorical."""

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

    class Meta:
        value_class = CategoryPointAnnotationStructValue


class CoordinatePointAnnotationStructValue(PointAnnotationStructValue):
    def get_x_position(self) -> float:
        return cast(float, self.get("x_position"))


class CoordinatePointAnnotationBlock(BasePointAnnotationBlock):
    """Point annotation for when the x-axis is continuous/linear."""

    label = blocks.CharBlock(required=True)

    x_position = TextInputFloatBlock(label="X", required=True)
    y_position = TextInputFloatBlock(label="Y", required=True)

    class Meta:
        value_class = CoordinatePointAnnotationStructValue
