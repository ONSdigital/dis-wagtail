from typing import TYPE_CHECKING, Any

from wagtail.admin.mail import GroupApprovalTaskStateSubmissionEmailNotifier
from wagtail.models import AbstractGroupApprovalTask

if TYPE_CHECKING:
    from wagtail.models import TaskState


class GroupReviewTask(AbstractGroupApprovalTask):
    """A special workflow task model aimed to prevent the last editor from approving their own work."""

    @classmethod
    def get_description(cls) -> str:
        return "A workflow review task that requires the approver to be different than the last editor."

    class Meta:
        verbose_name = "Group review task"
        verbose_name_plural = "Group review tasks"


class ReadyToPublishGroupTask(AbstractGroupApprovalTask):
    """Placeholder task model to use in the Bundle approval logic."""

    @classmethod
    def get_description(cls) -> str:
        return "Marks a page as ready to be published. Used by bundles."

    class Meta:
        verbose_name = "Ready to publish task"
        verbose_name_plural = "Ready to publish tasks"


class TaskStateSubmissionEmailNotifier(GroupApprovalTaskStateSubmissionEmailNotifier):
    """A notifier to send email updates for our submission events."""

    def can_handle(self, instance: "TaskState", **kwargs: Any) -> bool:
        return isinstance(instance, self.valid_classes) and isinstance(
            instance.task.specific, GroupReviewTask | ReadyToPublishGroupTask
        )
