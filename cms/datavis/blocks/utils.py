from django.forms import TextInput
from wagtail import blocks


class TextInputCharBlock(blocks.IntegerBlock):
    """A text input widget that only allows numeric input.

    See https://design-system.service.gov.uk/components/text-input/#numbers
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.field.widget = TextInput(attrs={"inputmode": "numeric", "pattern": "[0-9]*"})


class TextInputFloatBlock(blocks.FloatBlock):
    """A text input widget that only allows decimal input.

    See https://design-system.service.gov.uk/components/text-input/#numbers
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # NB inputmode is not "decimal" as per the guidance linked in the docstring above
        self.field.widget = TextInput(attrs={"inputmode": "text", "pattern": "[0-9]*\\.?[0-9]*"})
