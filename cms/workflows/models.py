from typing import TYPE_CHECKING, Any

from wagtail.admin.mail import GroupApprovalTaskStateSubmissionEmailNotifier
from wagtail.models import AbstractGroupApprovalTask

from .locks import PageInBundleReadyToBePublishedLock

if TYPE_CHECKING:
    from django.db.models import Model
    from wagtail.models import TaskState

    from cms.bundles.models import Bundle
    from cms.users.models import User


class GroupReviewTask(AbstractGroupApprovalTask):
    """A special workflow task model aimed to prevent the last editor from approving their own work."""

    @classmethod
    def get_description(cls) -> str:
        return "A workflow review task that requires the approver to be different than the last editor."

    def user_can_unlock(self, obj: Model, user: User) -> bool:
        return user.has_perm("wagtailadmin.unlock_workflow_tasks")

    class Meta:
        verbose_name = "Group review task"
        verbose_name_plural = "Group review tasks"


class ReadyToPublishGroupTask(AbstractGroupApprovalTask):
    """Placeholder task model to use in the Bundle approval logic."""

    lock_class = PageInBundleReadyToBePublishedLock

    @classmethod
    def get_description(cls) -> str:
        return "Marks a page as ready to be published. Used by bundles."

    def locked_for_user(self, obj: Model, user: User) -> bool:
        active_bundle: Bundle | None = getattr(obj, "active_bundle", None)
        if active_bundle is not None and active_bundle.is_ready_to_be_published:
            return True

        locked: bool = super().locked_for_user(obj, user)
        return locked

    def user_can_unlock(self, obj: Model, user: User) -> bool:
        return user.has_perm("wagtailadmin.unlock_workflow_tasks")

    class Meta:
        verbose_name = "Ready to publish task"
        verbose_name_plural = "Ready to publish tasks"


class TaskStateSubmissionEmailNotifier(GroupApprovalTaskStateSubmissionEmailNotifier):
    """A notifier to send email updates for our submission events."""

    def can_handle(self, instance: TaskState, **kwargs: Any) -> bool:
        return isinstance(instance, self.valid_classes) and isinstance(
            instance.task.specific, GroupReviewTask | ReadyToPublishGroupTask
        )
