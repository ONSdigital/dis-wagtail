from typing import TYPE_CHECKING, Any

from django.db import transaction
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

    Accounts for when we're locked in ready to publish, when the workflow was "unlocked" (i.e. moved back a step)
    as well as scheduled publishing
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

    Locks the page so it cannot be edited while in review. The submitter (or a reviewer)
    can use 'Unlock editing' (reject) to unlock editing. Reviewers can approve to move
    to the next stage.

    Self-approval prevention: the last editor cannot approve their own work.
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

        - All users with access: 'Unlock editing' (reject with comment)
        - Reviewers (not the last editor): 'Approve', 'Approve with comment'
        """
        if not self.user_can_access_editor(obj, user):
            return []

        actions: list[tuple[str, str, bool]] = [
            ("reject", "Unlock editing", True),
        ]

        is_self_approver = obj.latest_revision and obj.latest_revision.user_id == user.pk  # type: ignore[attr-defined]
        if not is_self_approver:
            actions.extend(
                [
                    ("approve", "Approve", False),
                    ("approve", "Approve with comment", True),
                ]
            )

        return actions

    class Meta:
        verbose_name = "Group review task"
        verbose_name_plural = "Group review tasks"


class ReadyToPublishGroupTask(AbstractGroupApprovalTask):
    """The 'Ready to publish' workflow task.

    Locks the page so it cannot be edited. The user can 'Unlock editing' (reject)
    to unlock editing, or publish/approve to complete the workflow.
    """

    lock_class = PageWorkflowLock

    @classmethod
    def get_description(cls) -> str:
        return "Marks a page as ready to be published. Used by bundles."

    def get_actions(self, obj: Model, user: User) -> list[tuple[str, str, bool]]:
        """Actions available on the locked page.

        - Not in a bundle: 'Unlock editing' + 'Publish'
        - In a bundle not ready to publish: 'Unlock editing' only
        - In a bundle ready to publish: no actions (fully locked via bundle)
        """
        if not self.user_can_access_editor(obj, user):
            return []

        if in_bundle_ready_to_be_published(obj):
            # Fully locked via bundle — no actions until bundle is reverted.
            return []

        actions: list[tuple[str, str, bool]] = [
            ("reject", "Unlock editing", True),
        ]

        if not in_active_bundle(obj):
            if hasattr(obj, "permissions_for_user") and obj.permissions_for_user(user).can_publish():
                actions.append(("locked-approve", get_final_approve_label(obj, "Approve"), False))

        return actions

    def on_action(self, task_state: TaskState, user: User, action_name: str, **kwargs: Any) -> None:
        if action_name == "locked-approve":
            super().on_action(task_state, user, "approve", **kwargs)
        elif action_name == "reject":
            self._unlock_and_revert_to_review(task_state, user, **kwargs)
        else:
            super().on_action(task_state, user, action_name, **kwargs)

    @transaction.atomic
    def _unlock_and_revert_to_review(self, task_state: TaskState, user: User, **kwargs: Any) -> None:
        """Cancel this task and reject the In Preview task state, unlocking the page for editing.

        On resubmit, Wagtail's resume() reads current_task_state.task and restarts the workflow
        at In Preview, requiring re-approval before reaching Ready to Publish again.
        """
        workflow_state = task_state.workflow_state

        # Cancel the Ready to Publish task state manually rather than calling
        # task_state.cancel() because cancel() triggers workflow_state.update() which
        # would attempt to progress the workflow (finding the next task or finishing it).
        # We need to control the workflow state ourselves to point it at In Preview.
        task_state.status = TaskState.STATUS_CANCELLED
        task_state.finished_at = timezone.now()
        task_state.finished_by = user
        task_state.comment = kwargs.get("comment", "")
        task_state.save()
        task_state.log_state_change_action(user, "cancel")

        # Find the In Preview task state so resume() will restart there
        in_preview_task = workflow_state.workflow.tasks.exclude(pk=self.pk).first()
        in_preview_task_state = (
            workflow_state.task_states.filter(task=in_preview_task).order_by("-finished_at").first()
            if in_preview_task
            else None
        )

        if not in_preview_task_state:
            # Unexpected state — cancel the workflow entirely as a safe fallback.
            workflow_state.cancel(user=user)
            return

        # Point the workflow at the In Preview task state before rejecting it.
        # This ensures resume() will restart at In Preview on resubmit.
        workflow_state.current_task_state = in_preview_task_state
        workflow_state.save(update_fields=["current_task_state"])

        # Set to IN_PROGRESS so reject() accepts it — reject() guards against
        # rejecting non-in-progress states. This keeps us aligned with core's reject
        # behaviour (signals, logging, future additions).
        in_preview_task_state.status = TaskState.STATUS_IN_PROGRESS
        in_preview_task_state.reject(user=user, comment=kwargs.get("comment", ""))

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
