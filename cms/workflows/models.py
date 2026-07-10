from typing import TYPE_CHECKING, Any

from django.utils import timezone
from wagtail.admin.mail import GroupApprovalTaskStateSubmissionEmailNotifier
from wagtail.models import AbstractGroupApprovalTask, TaskState, WorkflowMixin

from cms.bundles.utils import in_active_bundle, in_bundle_ready_to_be_published

from .locks import PageWorkflowLock

if TYPE_CHECKING:
    from django.db.models import Model

    from cms.users.models import User


def get_final_approve_label(obj: WorkflowMixin, label: str) -> str:
    """Tidies up the "approve" action label.

    Accounts for when we're locked in ready to publish, as well as scheduled publishing.
    """
    with_comment = "with comment" in label

    is_final_task = (
        obj.current_workflow_task
        and obj.current_workflow_task.pk == obj.current_workflow_state.workflow.tasks.last().pk
    )
    if is_final_task:
        if (go_live_at := getattr(obj, "go_live_at", None)) and go_live_at > timezone.now():
            label = "Schedule to publish"
        else:
            label = "Publish"
    else:
        label = "Approve"

    if with_comment:
        label += " with comment"

    return label


class GroupReviewTask(AbstractGroupApprovalTask):
    """The 'In Preview' workflow task.

    Locks the page so it cannot be edited while in review. Users can 'Return to draft'
    (via the unlock view which cancels the workflow) to unlock editing.
    Reviewers (not the last editor) can approve to move to the next stage.
    """

    lock_class = PageWorkflowLock

    @classmethod
    def get_description(cls) -> str:
        return (
            "A workflow review task that locks the page and requires the approver to be different than the last editor."
        )

    def locked_for_user(self, obj: Model, user: User) -> bool:
        """Page is locked for all users while in preview."""
        return True

    def user_can_lock(self, obj: Model, user: User) -> bool:
        """Disable manual locks as the workflow lock handles this."""
        return False

    def user_can_unlock(self, obj: Model, user: User) -> bool:
        """Used for manual locks."""
        return user.has_perm("wagtailadmin.unlock_workflow_tasks")

    def get_actions(self, obj: Model, user: User) -> list[tuple[str, str, bool]]:
        """Actions available on the locked page.

        - Reviewers (not the last editor): 'Approve', 'Approve with comment'
        - 'Return to draft' is handled separately via the unlock view, not as a workflow action.
        """
        if not self.user_can_access_editor(obj, user):
            return []

        is_self_approver = obj.latest_revision and obj.latest_revision.user_id == user.pk  # type: ignore[attr-defined]
        if is_self_approver:
            return []

        return [
            ("approve", "Approve", False),
            ("approve", "Approve with comment", True),
        ]

    class Meta:
        verbose_name = "Group review task"
        verbose_name_plural = "Group review tasks"


class ReadyToPublishGroupTask(AbstractGroupApprovalTask):
    """The 'Ready to publish' workflow task.

    Locks the page so it cannot be edited. Users can 'Return to draft' (via the unlock view
    which cancels the workflow) to unlock editing, or publish to complete the workflow.
    """

    lock_class = PageWorkflowLock

    @classmethod
    def get_description(cls) -> str:
        return "Marks a page as ready to be published. Used by bundles."

    def get_actions(self, obj: Model, user: User) -> list[tuple[str, str, bool]]:
        """Actions available on the locked page.

        - Not in a bundle: 'Publish' (or 'Schedule to publish')
        - In a bundle not ready to publish: no workflow actions (only 'Return to draft' via view)
        - In a bundle ready to publish: no actions (fully locked via bundle)

        'Return to draft' is handled separately via the unlock view.
        """
        if not self.user_can_access_editor(obj, user):
            return []

        if in_bundle_ready_to_be_published(obj):
            # Fully locked via bundle — no actions until bundle is reverted.
            return []

        if not in_active_bundle(obj):
            if hasattr(obj, "permissions_for_user") and obj.permissions_for_user(user).can_publish():
                return [("locked-approve", get_final_approve_label(obj, "Approve"), False)]

        return []

    def on_action(self, task_state: TaskState, user: User, action_name: str, **kwargs: Any) -> None:
        if action_name == "locked-approve":
            super().on_action(task_state, user, "approve", **kwargs)
        else:
            super().on_action(task_state, user, action_name, **kwargs)

    def locked_for_user(self, obj: Model, user: User) -> bool:
        """Marked as locked regardless of user, or bundle."""
        return True

    def user_can_lock(self, obj: Model, user: User) -> bool:
        """Disable manual locks as we lock this."""
        return False

    def user_can_unlock(self, obj: Model, user: User) -> bool:
        """Used for when the page is manually locked."""
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
