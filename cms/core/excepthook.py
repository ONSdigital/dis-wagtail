import logging
import sys
import threading
from types import TracebackType

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def except_hook(exception_type: type[BaseException], exception: BaseException, traceback: TracebackType | None) -> None:
    """A custom exception hook which displays the exception as JSON."""
    if exception_type is SyntaxError:
        # Show syntax errors more easily
        sys.__excepthook__(exception_type, exception, traceback)
    else:
        logger.exception("Unhandled exception", exc_info=exception)


def threading_except_hook(args: threading.ExceptHookArgs) -> None:
    """A custom exception hook which displays the exception as JSON."""
    if args.exc_value is None:
        # If there's no exception, fall back to default hook
        threading.__excepthook__(args)
    else:
        logger.exception(
            "Unhandled exception in thread",
            exc_info=args.exc_value,
            extra={
                "native_thread_id": args.thread.native_id if args.thread else None,
                "thread_id": args.thread.ident if args.thread else None,
            },
        )


def register_except_hook() -> None:
    if sys.excepthook is not sys.__excepthook__:
        raise ImproperlyConfigured(f"Except hook has already been configured: {sys.excepthook}")

    if threading.excepthook is not threading.__excepthook__:
        raise ImproperlyConfigured(f"Threading except hook has already been configured: {sys.excepthook}")

    sys.excepthook = except_hook
    threading.excepthook = threading_except_hook
