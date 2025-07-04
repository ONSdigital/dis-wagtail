from typing import Any, cast

from django.forms import FloatField, TextInput
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

        # TODO remove this once we upgrade to a Wagtail version in which
        # https://github.com/wagtail/wagtail/pull/13206 is merged.
        self.field_workaround(**kwargs)

        # NB inputmode is intentionally not "decimal" as per the guidance linked
        # in the docstring above
        self.field.widget = TextInput(attrs={"inputmode": "text"})

    def field_workaround(self, **kwargs: Any) -> None:
        """Workaround for help_text not being passed to FloatBlock in Wagtail.
        See https://github.com/wagtail/wagtail/issues/13205.

        Note that this is called after super().__init__() in self.__init__(),
        but that's fine as self.field is not touched in the parent Block class
        __init__ method.

        This can be removed once https://github.com/wagtail/wagtail/pull/13206
        is merged.
        """
        help_text = cast(str | None, kwargs.get("help_text"))
        self.field = FloatField(
            required=kwargs.get("required", True),
            max_value=kwargs.get("max_value"),
            min_value=kwargs.get("min_value"),
            validators=kwargs.get("validators", ()),
            help_text=help_text or "",
        )
