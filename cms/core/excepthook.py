import logging
import sys
from types import TracebackType

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def except_hook(exception_type: type[BaseException], exception: BaseException, traceback: TracebackType | None) -> None:
    """A custom exception hook which displays the exception as JSON."""
    if exception_type is SyntaxError:
        # Show syntax errors more easily. They're not correctly handled by our logger for some reason
        sys.__excepthook__(exception_type, exception, traceback)
    else:
        logger.exception("Unhandled exception", exc_info=exception)


def register_except_hook() -> None:
    if sys.excepthook is not sys.__excepthook__:
        raise ImproperlyConfigured(f"Except hook has already been configured: {sys.excepthook}")

    sys.excepthook = except_hook
