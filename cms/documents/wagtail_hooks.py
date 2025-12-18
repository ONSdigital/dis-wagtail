"""Wagtail hooks for document audit logging."""

from typing import TYPE_CHECKING

from wagtail import hooks
from wagtail.log_actions import log

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.documents.models import CustomDocument


@hooks.register("after_create_document")
def log_document_create(request: "HttpRequest", document: "CustomDocument") -> None:
    """Log document creation for audit trail.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#after-create-document
    """
    log(action="wagtail.create", instance=document)


@hooks.register("after_edit_document")
def log_document_edit(request: "HttpRequest", document: "CustomDocument") -> None:
    """Log document edits for audit trail.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#after-edit-document
    """
    log(action="wagtail.edit", instance=document)


@hooks.register("after_delete_document")
def log_document_delete(request: "HttpRequest", document: "CustomDocument") -> None:
    """Log document deletion for audit trail.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#after-delete-document
    """
    log(action="wagtail.delete", instance=document)
