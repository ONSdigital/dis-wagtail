from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.documents.permissions import permission_policy

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.utils.safestring import SafeString

    from cms.private_media.models import AbstractPrivateDocument


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
        static("private_media/js/image-modal-overrides.js"),
        static("private_media/js/document-modal-overrides.js"),
    )


@hooks.register("before_serve_document")
def protect_private_documents(document: "AbstractPrivateDocument", request: "HttpRequest") -> None:
    """Block access to private documents if the user has insufficient permissions."""
    if document.is_private and (
        not request.user.is_authenticated
        or not permission_policy.user_has_any_permission_for_instance(
            request.user, ["choose", "add", "change"], document
        )
    ):
        raise PermissionDenied
