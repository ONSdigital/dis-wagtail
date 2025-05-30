from typing import Any, ClassVar

from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock
from cms.datavis.constants import AxisType


class AnnotationStructValue(StructValue):
    X_AXIS_TYPE: ClassVar[AxisType]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not hasattr(self, "X_AXIS_TYPE"):
            raise RuntimeError("Subclass must set X_AXIS_TYPE")

    def get_config(self) -> dict[str, Any]:
        return {
            "text": self.get("label"),
        }

    def get_label_offsets(self) -> dict[str, int]:
        if label_offset_y := self.get("label_offset_y"):
            # The SVG coordinate system measures from the top left. It makes more sense
            # to users to measure from the bottom left, to match the chart coordinates.
            label_offset_y = -label_offset_y
        return {
            "labelOffsetX": self.get("label_offset_x"),
            "labelOffsetY": label_offset_y,
        }

    def get_x_position(self, x_position: int | float) -> int | float:
        match self.X_AXIS_TYPE:
            case AxisType.CATEGORICAL:
                # The Design System component expects 0-based indices. We have a 1-based UI.
                return int(x_position - 1)
            case AxisType.LINEAR:
                return x_position


class PointAnnotationStructValue(AnnotationStructValue):
    def get_config(self) -> dict[str, Any]:
        config = super().get_config()
        config["point"] = {
            "x": self.get_x_position(self.get("x_position")),
            "y": self.get("y_position"),
        }
        config.update(self.get_label_offsets())
        return config


class BasePointAnnotationBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)
    x_position = blocks.StaticBlock()
    y_position = blocks.StaticBlock()
    label_offsets = blocks.StaticBlock(admin_text="Offsets are measured in pixels")
    label_offset_x = TextInputIntegerBlock(label="Offset X", default=0)
    label_offset_y = TextInputIntegerBlock(label="Offset Y", default=0)


class PointAnnotationCategoricalStructValue(PointAnnotationStructValue):
    X_AXIS_TYPE = AxisType.CATEGORICAL


class PointAnnotationCategoricalBlock(BasePointAnnotationBlock):
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
        value_class = PointAnnotationCategoricalStructValue


class PointAnnotationLinearStructValue(PointAnnotationStructValue):
    X_AXIS_TYPE = AxisType.LINEAR


class PointAnnotationLinearBlock(BasePointAnnotationBlock):
    """Point annotation for when the x-axis is continuous/linear."""

    label = blocks.CharBlock(required=True)

    x_position = TextInputFloatBlock(label="X", required=True)
    y_position = TextInputFloatBlock(label="Y", required=True)

    class Meta:
        value_class = PointAnnotationLinearStructValue
