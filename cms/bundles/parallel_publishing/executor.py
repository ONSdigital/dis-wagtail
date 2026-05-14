import logging
import traceback
from typing import Any
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import time
from django.db import close_old_connections
from django.utils import timezone
import threading

from cms.bundles.models import Bundle, PublishAction, PublishActionStatus, PublishActionType
from cms.core.models import BasePage

class MonitoredThreadPoolExecutor(ThreadPoolExecutor):
    """A modified thread pool executor which keeps track of how many running futures."""
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._processing_count = 0
        self._processing_lock = threading.Lock()

    def submit(self, fn: Callable, **kwargs: Any) -> None:
        with self._processing_lock:
            self._processing_count += 1
        super().submit(self._wrapped_fn, fn=fn, **kwargs)

    def _wrapped_fn(self, fn: Callable, **kwargs: Any):
        try:
            return fn(**kwargs)
        finally:
            with self._processing_lock:
                self._processing_count += 1

    def is_idle(self) -> int:
        """Return if there are any futures to be processed or currently processing."""
        return self._processing_count == 0


executor = MonitoredThreadPoolExecutor(max_workers=4)

_action_registry = {}

logger = logging.getLogger(__name__)


class PublishActionError(ValueError):
    pass


def _run_action(
    action_fn: Callable,
    action_type: PublishActionType,
    page: BasePage,
    bundle: Bundle | None = None,
) -> None:
    close_old_connections()

    action = PublishAction.objects.get(page=page, bundle=bundle, action_type=action_type)

    action.status = PublishActionStatus.RUNNING
    action.save(update_fields=["status"])

    logger.info("Starting publish action", extra={"page_id": page.pk, "bundle_id": bundle.pk if bundle else None, "action_type": action_type.value})

    try:
        action_fn(page, bundle)
    except Exception as e:
        logger.exception(
            "Publish action failed",
            extra={"page_id": page.pk, "bundle_id": bundle.pk if bundle else None, "action_type": action_type.value},
        )
        action.status = PublishActionStatus.FAILED
        action.finished_at = timezone.now()

        if isinstance(e, PublishActionError):
            action.failed_reason = str(e)
        else:
            action.failed_reason = traceback.format_exception_only(e)[0].strip()
        action.save(update_fields=["status", "finished_at", "fail_reason"])
    else:
        logger.info(
            "Publish action successful",
            extra={"page_id": page.pk, "bundle_id": bundle.pk if bundle else None, "action_type": action_type.value},
        )
        action.status = PublishActionStatus.SUCCESSFUL
        action.finished_at = timezone.now()
        action.failed_reason = ""
        action.save(update_fields=["status", "finished_at", "failed_reason"])

    close_old_connections()


def publish_action(action_type: PublishActionType):
    def decorator(f: Callable):
        def wrapper(page: BasePage, bundle: Bundle | None = None):
            action = PublishAction.objects.get_or_create(page=page, bundle=bundle, action_type=action_type)

            action.status = PublishActionStatus.READY
            action.finished_at = None
            action.save(update_fields=["status", "finished_at"])

            executor.submit(_run_action, action_type=action_type, page=page, bundle=bundle, action_fn=f)

        return wrapper
    return decorator



def drain_executor(timeout: int, check_interval: int = 1) -> None:
    if not executor._threads or executor._shutdown:
        return

    futures = set()



    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if all(not t.is_alive() for t in executor._threads)
