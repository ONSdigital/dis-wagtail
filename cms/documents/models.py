from cms.private_media.models import AbstractPrivateDocument


class CustomDocument(AbstractPrivateDocument):
    """Custom Wagtail document class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """
