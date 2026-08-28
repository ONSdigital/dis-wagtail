import textwrap
from typing import TYPE_CHECKING

from cms.bundles.clients.api import BundleAPIClientError

if TYPE_CHECKING:
    from django.forms import BaseForm


def add_exception_cause_to_form(exception: Exception, *, form: BaseForm) -> None:
    """Adds errors from a BundleAPIClientError exception cause to the form errors."""
    cause = getattr(exception, "__cause__", None)
    if not cause:
        return

    # Currently only handle BundleAPIClientError causes
    if not isinstance(cause, BundleAPIClientError):
        return

    for error in cause.errors:
        desc = error.get("description") or "Unknown API Error"
        form.add_error(
            field=None,
            error=textwrap.shorten(desc, width=250, placeholder="..."),  # limit chars to avoid overly long errors
        )
