from typing import Any

from django.db.models import IntegerChoices
from django.forms import TypedChoiceField
from wagtail import blocks


class AspectRatioBlock(blocks.ChoiceBlock):
    class AspectRatioChoices(IntegerChoices):
        _1_1 = int(100 / 1), "1:1"
        _4_3 = int(100 / (4 / 3)), "4:3"
        _16_9 = int(100 / (16 / 9)), "16:9"
        _21_9 = int(100 / (21 / 9)), "21:9"
        _10_3 = int(100 / (10 / 3)), "10:3"

        __empty__ = "Default"

    choices = AspectRatioChoices.choices

    def get_field(self, **kwargs: Any) -> TypedChoiceField:
        """Coerce choices to integers, or None.

        The Design System expects aspect ratios as integer percentages. To
        revert to the default behaviour, the key must be either omitted or set
        to `null`.
        """
        return TypedChoiceField(coerce=int, empty_value=None, **kwargs)
