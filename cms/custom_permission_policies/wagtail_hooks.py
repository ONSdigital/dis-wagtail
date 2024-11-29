from typing import TYPE_CHECKING

from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


@hooks.register("insert_editor_js")
def load_chooser_modal_override_js() -> "SafeString":
    """Load JS overrides for the image and document chooser modals, which
    get them to include the current URL as a query parameter when the modal
    is opened (allowing the chooser views to determine the 'parent object').
    """
    return format_html(
        """
        <script src="{0}"></script>
        <script src="{1}"></script>
        """,
        static("custom_permission_policies/js/image-modal-overrides.js"),
        static("custom_permission_policies/js/document-modal-overrides.js"),
    )
