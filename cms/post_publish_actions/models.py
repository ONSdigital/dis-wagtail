from typing import ClassVar, Self

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PostPublishActionType(models.TextChoices):
    S3_ACL = "S3_ACL", _("Private Media ACLs")
    SEARCH_UPDATED = "SEARCH_UPDATED", _("Search updated")


class PostPublishActionStatus(models.TextChoices):
    READY = ("READY", _("Ready"))
    RUNNING = ("RUNNING", _("Running"))
    FAILED = ("FAILED", _("Failed"))
    SUCCESSFUL = ("SUCCESSFUL", _("Successful"))


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
        choices=PostPublishActionType,
        max_length=max(len(value) for value in PostPublishActionType.values),
    )
    bundle = models.ForeignKey("bundles.Bundle", null=True, on_delete=models.CASCADE)
    page = models.ForeignKey("wagtailcore.Page", on_delete=models.CASCADE)
    status = models.CharField(
        choices=PostPublishActionStatus,
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
        indexes: ClassVar[list[models.Index]] = [
            models.Index("bundle", "page", "action_type", name="publish_action_relation")
        ]

    def __str__(self) -> str:
        return f"{self.action_type} for {self.page_id} in bundle {self.bundle_id} (status: {self.status}) ({self.pk})"
