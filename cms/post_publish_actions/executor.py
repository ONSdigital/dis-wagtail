import logging
import time
import traceback
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from functools import partial
from typing import Any

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from cms.core.db_router import force_write_db

from .models import PostPublishAction, PostPublishActionStatus, PostPublishActionType


def _build_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(
        max_workers=settings.BUNDLE_POST_PUBLISH_CONCURRENCY, thread_name_prefix="post_publish_actions"
    )


_executor = _build_executor()

logger = logging.getLogger(__name__)


def _executor_wrapper[**P](executor_fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> Any:
    close_old_connections()

    try:
        executor_fn(*args, **kwargs)
    finally:
        close_old_connections()


@force_write_db()
def run_action(
    action_handler: Callable,
    action_type: PostPublishActionType,
    page_id: int,
    bundle_id: int | None,
) -> None:
    # TODO: Support page-only publishes
    if bundle_id is None:
        raise RuntimeError("Bundle id required")

    action = PostPublishAction.objects.get(page_id=page_id, bundle_id=bundle_id, action_type=action_type)
    action.status = PostPublishActionStatus.RUNNING
    action.save(update_fields=["status"])

    logger.info(
        "Starting publish action",
        extra={
            "page_id": page_id,
            "bundle_id": bundle_id,
            "action_type": action_type.value,
            "event": "post_publish_action_start",
        },
    )
    start_time = time.perf_counter()

    try:
        action_handler()
    except Exception as e:  # pylint: disable=broad-exception-caught
        duration = time.perf_counter() - start_time
        logger.exception(
            "Publish action failed",
            extra={
                "page_id": page_id,
                "bundle_id": bundle_id,
                "action_type": action_type.value,
                "event": "post_publish_action_failed",
                "duration": duration,
            },
        )
        action.status = PostPublishActionStatus.FAILED
        action.duration = timedelta(seconds=duration)
        action.finished_at = timezone.now()
        action.failed_reason = traceback.format_exception_only(e)[0].strip()
        action.save(update_fields=["status", "finished_at", "fail_reason", "duration"])
    else:
        duration = time.perf_counter() - start_time
        logger.info(
            "Publish action successful",
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
    global _executor  # noqa: PLW0603 # pylint: disable=global-statement
    _executor.shutdown(wait=True)

    _executor = _build_executor()


def run_in_executor[**P](fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> Future:
    return _executor.submit(partial(_executor_wrapper, fn, *args, **kwargs))
