from wagtail import blocks


class RelativeOrAbsoluteURLBlock(blocks.URLBlock):
    """A URLBlock that accepts both relative and absolute URLs.
    This is required because Wagtail's built-in URLBlock only accepts absolute URLs,
    an inherited and intentional limitation from Django's URLField.
    """

    def clean(self, value):
        # If the value starts with "/" we assume it is a relative URL, and prepend a dummy scheme and domain
        # This allows us to leverage the URLBlock validation for relative URLs.
        # Note that this does mean that some validation e.g. max length will include this dummy prefix in their count,
        # which should be considered when setting those limits.
        value = f"https://example.com{value}" if value and value.startswith("/") else value
        cleaned = super().clean(value)
        return cleaned
