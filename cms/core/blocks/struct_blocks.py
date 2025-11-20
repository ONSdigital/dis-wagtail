from wagtail import blocks


class RelativeOrAbsoluteURLBlock(blocks.URLBlock):
    """A URLBlock that accepts both relative and absolute URLs.
    This is required because Wagtail's built-in URLBlock only accepts absolute URLs,
    an inherited and intentional limitation from Django's URLField.
    """

    def clean(self, value):
        # If the value starts with "/" we assume it is a relative URL, and prepend a minimal dummy domain "a.aa",
        # otherwise we assume it is an absolute URL and leave it unchanged.
        # This allows us to leverage the URLBlock validation for relative URLs.
        # Note that this does mean that validation e.g. max length will include this dummy prefix which should be
        # considered carefully if setting those limits, the url being validated will be longer than the relative URL
        # input. If exact length validation is required for a particular use case, this block may not be suitable.
        absolute_value = f"https://a.aa{value}" if value and value.startswith("/") else value

        # Pass the definitely absolute URL shaped value to the parent clean method for validation
        super().clean(absolute_value)

        # Return the original value, not the return from the super clean call.
        # This is safe in this specific scenario because URL cleaning does not modify the value, only validates it
        return value
