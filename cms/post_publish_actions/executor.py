import logging
import os
import time
import traceback
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import timedelta
from functools import partial

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from wagtail.models import Page

from cms.core.db_router import force_write_db
from cms.core.utils import release_db_connections

from .models import PostPublishAction, PostPublishActionStatus, PostPublishActionType
from .registry import ActionHandler

SHUTDOWN_MESSAGE_BUFFER_SECONDS = 5


def _build_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(
        max_workers=settings.BUNDLE_POST_PUBLISH_CONCURRENCY, thread_name_prefix="post_publish_actions"
    )


def _build_support_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(
        max_workers=settings.BUNDLE_POST_PUBLISH_SUPPORT_CONCURRENCY, thread_name_prefix="post_publish_actions_support"
    )


# The main executor is reserved exclusively for post-publish actions
_executor = _build_executor()

# The "support" executor should be used for ancillary tasks
_support_executor = _build_support_executor()

logger = logging.getLogger(__name__)


def _executor_wrapper[**P](executor_fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> None:
    close_old_connections()

    try:
        executor_fn(*args, **kwargs)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Unhandled exception in post-publish actions")
    finally:
        close_old_connections()


@force_write_db()
def run_action(
    action_handler: ActionHandler,
    action_type: PostPublishActionType,
    page_id: int,
    bundle_id: int | None,
) -> None:
    from cms.bundles.models import Bundle  # pylint: disable=import-outside-toplevel

    # TODO: Support page-only publishes
    if bundle_id is None:
        raise RuntimeError("Bundle id required")

    action = PostPublishAction.objects.get(page_id=page_id, bundle_id=bundle_id, action_type=action_type)
    action.status = PostPublishActionStatus.RUNNING
    action.save(update_fields=["status"])

    # use `specific` to ensure pages are cast to their subclass
    # guarantees class attributes are available in post-publish actions
    page = Page.objects.get(id=page_id).specific
    bundle = Bundle.objects.get(id=bundle_id)

    logger.info(
        "Starting post-publish action",
        extra={
            "page_id": page_id,
            "bundle_id": bundle_id,
            "action_type": action_type.value,
            "event": "post_publish_action_start",
        },
    )

    # Close connection just before running handler. If the handler doesn't touch the DB,
    # this frees up a connection for another thread to use.
    close_old_connections()

    start_time = time.perf_counter()
    try:
        action_handler(page, bundle)
    except Exception as e:  # pylint: disable=broad-exception-caught
        duration = time.perf_counter() - start_time
        logger.exception(
            "Post-publish action failed",
            extra={
                "page_id": page_id,
                "bundle_id": bundle_id,
                "action_type": action_type.value,
                "event": "post_publish_action_failed",
                "duration": duration,
            },
        )
        action.status = PostPublishActionStatus.FAILED
        action.finished_at = timezone.now()
        action.failed_reason = traceback.format_exception_only(e)[0].strip()
        action.duration = timedelta(seconds=duration)
        action.save(update_fields=["status", "finished_at", "failed_reason", "duration"])
    else:
        duration = time.perf_counter() - start_time
        logger.info(
            "Post-publish action successful",
            extra={
                "page_id": page_id,
                "bundle_id": bundle_id,
                "action_type": action_type.value,
                "event": "post_publish_action_successful",
                "duration": duration,
            },
        )
        action.status = PostPublishActionStatus.SUCCESSFUL
        action.finished_at = timezone.now()
        action.failed_reason = ""
        action.duration = timedelta(seconds=duration)
        action.save(update_fields=["status", "finished_at", "failed_reason", "duration"])


def flush_executor() -> None:
    global _executor, _support_executor  # noqa: PLW0603 # pylint: disable=global-statement
    _executor.shutdown(wait=True)
    _support_executor.shutdown(wait=True)
    _bundle_notification_futures.clear()

    _executor = _build_executor()
    _support_executor = _build_support_executor()


def _reset_executors_after_fork() -> None:
    """Rebuild executors in child process after a fork."""
    global _executor, _support_executor  # noqa: PLW0603 # pylint: disable=global-statement

    _bundle_notification_futures.clear()

    _executor = _build_executor()
    _support_executor = _build_support_executor()


os.register_at_fork(after_in_child=_reset_executors_after_fork)


def run_in_executor[**P](fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> Future:
    return _executor.submit(partial(_executor_wrapper, fn, *args, **kwargs))


def run_in_support_executor[**P](fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> Future:
    return _support_executor.submit(partial(_executor_wrapper, fn, *args, **kwargs))


_bundle_notification_futures: dict[int, Future] = {}


def _run_after[**P](previous: Future | None, fn: Callable[P, None], /, *args: P.args, **kwargs: P.kwargs) -> None:
    if previous is not None:
        wait([previous])
    fn(*args, **kwargs)


def run_bundle_notification_in_support_executor[**P](
    bundle_id: int, fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs
) -> Future:
    previous = _bundle_notification_futures.get(bundle_id)
    future = run_in_support_executor(_run_after, previous, fn, *args, **kwargs)
    _bundle_notification_futures[bundle_id] = future
    return future


@release_db_connections
def wait_for_bundle_notifications(bundle_id: int) -> None:
    if future := _bundle_notification_futures.pop(bundle_id, None):
        wait([future])


def executor_stop_and_wait(progress: bool = False) -> None:
    """Shutdown the executors, and wait for them to completely stop.

    This is similar to .shutdown(wait=True), but with optional progress reporting.
    """
    _executor.shutdown(wait=False)
    _support_executor.shutdown(wait=False)

    # Give the threads time to terminate to avoid unnecessary printing.
    if progress:
        time.sleep(0.1)

    executor_threads = _executor._threads | _support_executor._threads  # pylint: disable=protected-access

    # Add 1 to force a print the first time around
    last_running_threads = len(executor_threads) + 1

    shutdown_notify_at = time.monotonic() + max(
        settings.BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS - SHUTDOWN_MESSAGE_BUFFER_SECONDS, 0
    )
    shutdown_notified = False

    while running_threads := [t for t in executor_threads if t.is_alive()]:
        if progress and last_running_threads > len(running_threads):
            logger.info(
                "Waiting for %d threads running post-publish actions",
                len(running_threads),
                extra={
                    "thread_ids": [t.native_id for t in running_threads],
                    "thread_names": [t.name for t in running_threads],
                },
            )
            last_running_threads = len(running_threads)

        if not shutdown_notified and time.monotonic() >= shutdown_notify_at:
            logger.error(
                "Post-publish actions still running at shutdown",
                extra={
                    "event": "post_publish_action_shutdown_timeout",
                    "thread_count": len(running_threads),
                    "thread_ids": [t.native_id for t in running_threads],
                    "thread_names": [t.name for t in running_threads],
                },
            )
            shutdown_notified = True

        time.sleep(0.1)
