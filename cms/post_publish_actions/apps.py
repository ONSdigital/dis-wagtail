import threading

from django.apps import AppConfig


class PostPublishActionsAppConfig(AppConfig):
    name = "cms.post_publish_actions"

    def ready(self) -> None:
        from .executor import executor_stop_and_wait  # pylint: disable=import-outside-toplevel

        # ThreadPoolExecutor threads are waited on when the process terminates.
        # This adds some logging to make it clear the process didn't hang.
        # This must be done using _register_atexit rather than atexit.register
        # as atexit runs after threads have joined.
        threading._register_atexit(executor_stop_and_wait)  # type: ignore[attr-defined] # pylint: disable=protected-access
