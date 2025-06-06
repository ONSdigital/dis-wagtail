from typing import Any, ClassVar, cast

from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.utils import TextInputFloatBlock, TextInputIntegerBlock
from cms.datavis.constants import AxisChoices, AxisType, BarColumnAxisChoices


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

    def get_label_offset_y(self) -> int | None:
        label_offset_y = cast(int | None, self.get("label_offset_y"))
        if label_offset_y is not None:
            # The SVG coordinate system measures from the top left. It makes more sense
            # to users to measure from the bottom left, to match the chart coordinates.
            label_offset_y = -label_offset_y
        return label_offset_y

    def get_label_offsets(self) -> dict[str, int | None]:
        return {
            "labelOffsetX": self.get("label_offset_x"),
            "labelOffsetY": self.get_label_offset_y(),
        }

    def get_x_position(self, x_position: int | float) -> int | float:
        match self.X_AXIS_TYPE:
            case AxisType.CATEGORICAL:
                # The Design System component expects 0-based indices. We have a 1-based UI.
                return int(x_position - 1)
            case AxisType.LINEAR:
                return x_position
            case _:
                raise NotImplementedError(f"Method .get_x_position() does not support axis type {self.X_AXIS_TYPE}")


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

    class Meta:
        icon = "location-crosshairs"


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


class RangeAnnotationStructValue(AnnotationStructValue):
    def get_config(self) -> dict[str, Any]:
        config = super().get_config()
        label_inside = self.get("label_inside")

        config.update(
            {
                "axis": self.get("axis"),
                "labelInside": label_inside,
            }
        )

        if self.get("axis") == AxisChoices.X:
            # X-axis can be categorical or linear
            config.update(
                {
                    "range": {
                        "axisValue1": self.get_x_position(self.get("start_position")),
                        "axisValue2": self.get_x_position(self.get("end_position")),
                    }
                }
            )
        else:
            # Y-axis is always linear
            config.update(
                {
                    "range": {
                        "axisValue1": self.get("start_position"),
                        "axisValue2": self.get("end_position"),
                    }
                }
            )

        # Only apply custom label positioning if permitted
        if label_inside is False:
            config.update(self.get_label_offsets())
            config["labelWidth"] = self.get("label_width")

        return config


class BaseRangeAnnotationBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)

    axis = blocks.ChoiceBlock(choices=AxisChoices.choices, default=AxisChoices.X)
    start_position = TextInputFloatBlock(label="Start position")
    end_position = TextInputFloatBlock(label="End position")

    label_inside = blocks.BooleanBlock(
        default=True, required=False, help_text="Adapt label width to fit the shaded area."
    )

    custom_label_positioning = blocks.StaticBlock(admin_text="Measurements are in pixels.")
    label_offset_x = TextInputIntegerBlock(label="Offset X", required=False)
    label_offset_y = TextInputIntegerBlock(label="Offset Y", required=False)
    label_width = TextInputIntegerBlock(label="Label width", required=False)

    ERROR_ORDERING = "error_ordering"
    ERROR_LABEL_INSIDE_CUSTOM_POSITIONING = "error_label_inside_custom_positioning"

    class Meta:
        icon = "square"

    def clean(self, value: dict[str, Any]) -> dict[str, Any]:
        cleaned_data: dict[str, Any] = super().clean(value)
        errors: dict[str, ValidationError] = {}

        if cleaned_data["start_position"] >= cleaned_data["end_position"]:
            errors["start_position"] = ValidationError(
                "Start position must be less than end position", code=self.ERROR_ORDERING
            )

        if cleaned_data["label_inside"]:
            for key in ["label_offset_x", "label_offset_y", "label_width"]:
                if cleaned_data[key] is not None:
                    label = self.child_blocks[key].label
                    errors[key] = ValidationError(
                        f"{label} cannot be set if 'label inside' is checked.",
                        code=self.ERROR_LABEL_INSIDE_CUSTOM_POSITIONING,
                    )

        if errors:
            raise blocks.StructBlockValidationError(block_errors=errors)
        return cleaned_data


class RangeAnnotationCategoricalStructValue(RangeAnnotationStructValue):
    X_AXIS_TYPE = AxisType.CATEGORICAL


class RangeAnnotationCategoricalBlock(BaseRangeAnnotationBlock):
    """For line and area charts where the x-axis is categorical."""

    ERROR_X_AXIS_MUST_BE_INTEGER = "error_x_axis_must_be_integer"

    class Meta:
        value_class = RangeAnnotationCategoricalStructValue

    def clean(self, value: dict[str, Any]) -> dict[str, Any]:
        cleaned_data: dict[str, Any] = super().clean(value)
        errors: dict[str, ValidationError] = {}

        # Require integers for the x-axis
        if cleaned_data["axis"] == AxisChoices.X:
            for position in ["start_position", "end_position"]:
                if not cleaned_data[position].is_integer():
                    errors[position] = ValidationError("Enter a whole number", code=self.ERROR_X_AXIS_MUST_BE_INTEGER)
                else:
                    cleaned_data[position] = int(cleaned_data[position])

        if errors:
            raise blocks.StructBlockValidationError(block_errors=errors)

        return cleaned_data


class RangeAnnotationBarColumnBlock(RangeAnnotationCategoricalBlock):
    """As categorical, but with different axis labels."""

    axis = blocks.ChoiceBlock(choices=BarColumnAxisChoices.choices, default=BarColumnAxisChoices.CATEGORY)

    class Meta:
        value_class = RangeAnnotationCategoricalStructValue


class RangeAnnotationLinearStructValue(RangeAnnotationStructValue):
    X_AXIS_TYPE = AxisType.LINEAR


class RangeAnnotationLinearBlock(BaseRangeAnnotationBlock):
    class Meta:
        value_class = RangeAnnotationLinearStructValue


class LineAnnotationStructValue(AnnotationStructValue):
    def get_config(self) -> dict[str, Any]:
        config = super().get_config()

        config.update(
            {
                "axis": self.get("axis"),
                "labelWidth": self.get("label_width"),
            }
        )

        if self.get("axis") == AxisChoices.X:
            # X-axis can be categorical or linear
            config.update({"value": self.get_x_position(self.get("value"))})
        else:
            # Y-axis is always linear
            config.update({"value": self.get("value")})

        # Only apply custom label positioning if set:
        for key in ["label_offset_x", "label_offset_y"]:
            if self.get(key) is not None:
                config.update(self.get_label_offsets())

        return config


class BaseLineAnnotationBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)
    axis = blocks.ChoiceBlock(choices=AxisChoices.choices, default=AxisChoices.X)
    value = TextInputFloatBlock(label="Value", required=True)

    label_width = TextInputIntegerBlock(label="Label width", default=150, required=True)
    label_offsets = blocks.StaticBlock(admin_text="Offsets are measured in pixels")
    label_offset_x = TextInputIntegerBlock(label="Offset X", required=False)
    label_offset_y = TextInputIntegerBlock(label="Offset Y", required=False)

    class Meta:
        icon = "minus"


class LineAnnotationCategoricalStructValue(LineAnnotationStructValue):
    X_AXIS_TYPE = AxisType.CATEGORICAL


class LineAnnotationCategoricalBlock(BaseLineAnnotationBlock):
    ERROR_X_AXIS_MUST_BE_INTEGER = "error_x_axis_must_be_integer"

    class Meta:
        value_class = LineAnnotationCategoricalStructValue

    def clean(self, value: dict[str, Any]) -> dict[str, Any]:
        cleaned_data: dict[str, Any] = super().clean(value)

        errors: dict[str, ValidationError] = {}
        # Require integers for the x-axis
        if cleaned_data["axis"] == AxisChoices.X:
            if not cleaned_data["value"].is_integer():
                errors["value"] = ValidationError("Enter a whole number", code=self.ERROR_X_AXIS_MUST_BE_INTEGER)
            else:
                cleaned_data["value"] = int(cleaned_data["value"])

        if errors:
            raise blocks.StructBlockValidationError(block_errors=errors)

        return cleaned_data


class LineAnnotationBarColumnBlock(BaseLineAnnotationBlock):
    """As categorical, but with different axis labels."""

    axis = blocks.ChoiceBlock(choices=BarColumnAxisChoices.choices, default=BarColumnAxisChoices.CATEGORY)

    class Meta:
        value_class = LineAnnotationCategoricalStructValue


class LineAnnotationLinearStructValue(LineAnnotationStructValue):
    X_AXIS_TYPE = AxisType.LINEAR


class LineAnnotationLinearBlock(BaseLineAnnotationBlock):
    class Meta:
        value_class = LineAnnotationLinearStructValue
