from typing import Any

from django.forms import TextInput
from wagtail import blocks


class TextInputIntegerBlock(blocks.IntegerBlock):
    """A text input widget that only allows numeric input.

    See https://design-system.service.gov.uk/components/text-input/#numbers
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.field.widget = TextInput(attrs={"inputmode": "numeric"})


class TextInputFloatBlock(blocks.FloatBlock):
    """A text input widget that only allows decimal input.

    See https://design-system.service.gov.uk/components/text-input/#asking-for-decimal-numbers
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # NB inputmode is intentionally not "decimal" as per the guidance linked
        # in the docstring above
        self.field.widget = TextInput(attrs={"inputmode": "text"})
