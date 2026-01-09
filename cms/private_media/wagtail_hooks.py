from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from wagtail import hooks
from wagtail.documents.permissions import permission_policy

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.private_media.models import PrivateDocumentMixin


@hooks.register("before_serve_document")
def protect_private_documents(document: PrivateDocumentMixin, request: HttpRequest) -> None:
    """Block access to private documents if the user has insufficient permissions."""
    if document.is_private and (
        not request.user.is_authenticated
        or not permission_policy.user_has_any_permission_for_instance(
            request.user, ["choose", "add", "change"], document
        )
    ):
        raise PermissionDenied
