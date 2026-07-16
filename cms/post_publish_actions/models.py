from functools import partial
from typing import ClassVar, Self

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class PostPublishActionType(models.TextChoices):
    S3_ACL = "S3_ACL", "Private Media ACLs"
    SEARCH_UPDATED = "SEARCH_UPDATED", "Search updated"


class PostPublishActionStatus(models.TextChoices):
    READY = "READY", "Ready"
    RUNNING = "RUNNING", "Running"
    FAILED = "FAILED", "Failed"
    SUCCESSFUL = "SUCCESSFUL", "Successful"


class PostPublishActionQuerySet(models.QuerySet):
    def active(self) -> Self:
        """Exclude stale action types.
        These may be from previous deployments with different types.
        """
        return self.filter(action_type__in=PostPublishActionType.values)

    def finished(self) -> Self:
        return self.exclude(finished_at=None)

    def unfinished(self) -> Self:
        return self.filter(finished_at=None)

    def pending(self) -> Self:
        return self.active().unfinished()

    def completed(self) -> Self:
        return self.active().finished()

    def successful(self) -> Self:
        return self.completed().filter(status=PostPublishActionStatus.SUCCESSFUL)

    def failed(self) -> Self:
        return self.completed().filter(status=PostPublishActionStatus.FAILED)

    def mark_timed_out(self) -> int:
        now = timezone.now()
        return self.update(
            status=PostPublishActionStatus.FAILED,
            failed_reason="Timeout",
            duration=None,
            finished_at=now,
            timed_out_at=now,
        )


class PostPublishAction(models.Model):
    action_type = models.CharField(
        choices=PostPublishActionType.choices,
        max_length=max(len(value) for value in PostPublishActionType.values),
    )
    bundle = models.ForeignKey("bundles.Bundle", null=True, on_delete=models.CASCADE)
    page = models.ForeignKey("wagtailcore.Page", on_delete=models.CASCADE)
    status = models.CharField(
        choices=PostPublishActionStatus.choices,
        max_length=max(len(value) for value in PostPublishActionStatus.values),
        default=PostPublishActionStatus.READY,
    )
    failed_reason = models.TextField(default="")
    enqueued_at = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(null=True)
    finished_at = models.DateTimeField(null=True)
    timed_out_at = models.DateTimeField(null=True)

    objects = PostPublishActionQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Page and type must be unique, optionally in the scope of a bundle
            models.UniqueConstraint(
                fields=["bundle", "page", "action_type"],
                condition=models.Q(bundle__isnull=False),
                name="bundle_page_type",
            ),
            models.UniqueConstraint(fields=["page", "action_type"], condition=models.Q(bundle=None), name="page_type"),
        ]

    def __str__(self) -> str:
        return (
            f"{self.action_type} for page {self.page_id} in bundle {self.bundle_id} (status: {self.status}) ({self.pk})"
        )

    def enqueue(self) -> None:
        from .executor import run_action, run_in_executor  # pylint: disable=import-outside-toplevel
        from .registry import get_post_publish_action_for_type  # pylint: disable=import-outside-toplevel

        action_type = PostPublishActionType[self.action_type]

        handler = partial(
            run_action,
            action_type=action_type,
            action_handler=get_post_publish_action_for_type(action_type),
            page_id=self.page_id,
            bundle_id=self.bundle_id,
        )

        # In tests, on_commit doesn't work as expected due to the wrapping transaction. Instead, support bypassing it
        # and running the handler immediately.
        if settings.BUNDLE_POST_PUBLISH_ACTION_SUBMIT_ON_COMMIT:
            # NB: It assumed that if this is run inside a transaction, that the transaction closes when the page has
            # finished publishing. This ensures the thread's view is of a published page.
            transaction.on_commit(
                partial(
                    run_in_executor,
                    handler,
                ),
            )
        else:
            run_in_executor(handler)
