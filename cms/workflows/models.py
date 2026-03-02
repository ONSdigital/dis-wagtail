from typing import TYPE_CHECKING, Any, Self

from django.db import transaction
from django.utils import timezone
from wagtail.admin.mail import GroupApprovalTaskStateSubmissionEmailNotifier
from wagtail.models import AbstractGroupApprovalTask, TaskState, WorkflowMixin

from cms.bundles.utils import in_active_bundle, in_bundle_ready_to_be_published

from .locks import PageReadyToBePublishedLock

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
    """A special workflow task model aimed to prevent the last editor from approving their own work."""

    @classmethod
    def get_description(cls) -> str:
        return "A workflow review task that requires the approver to be different than the last editor."

    def user_can_lock(self, obj: Model, user: User) -> bool:
        return self._user_in_groups(user) or user.is_superuser

    def user_can_unlock(self, obj: Model, user: User) -> bool:
        """Used for manual locks."""
        return user.has_perm("wagtailadmin.unlock_workflow_tasks")

    def get_actions(self, obj: Model, user: User) -> list[tuple[str, str, bool]]:
        # The user must be in the selected groups, or a superuser
        if not self.user_can_access_editor(obj, user):
            return []

        actions = [("reject", "Request changes", True)]

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
    """Placeholder task model to use in the Bundle approval logic."""

    lock_class = PageReadyToBePublishedLock

    @classmethod
    def get_description(cls) -> str:
        return "Marks a page as ready to be published. Used by bundles."

    def get_actions(self, obj: Model, user: User) -> list[tuple[str, str, bool]]:
        # The user must be in the selected groups, or a superuser
        if not self.user_can_access_editor(obj, user):
            return []

        # if not in a bundle -> unlock/approve (acts as publish when last task)
        # if locked, but not in bundle ready to be published -> unlock only
        # if lock and in bundle ready to be published -> []
        if not in_active_bundle(obj):
            actions = [("unlock", "Unlock editing", False)]
            if hasattr(obj, "permissions_for_user") and obj.permissions_for_user(user).can_publish():
                actions.append(("locked-approve", get_final_approve_label(obj, "Approve"), False))
            return actions
        if not in_bundle_ready_to_be_published(obj):
            # we're in a bundle which is not yet ready to be published,
            # so the only available option is to unlock.
            return [("unlock", "Unlock editing", False)]

        # we're in a bundle that is ready to be published. Cannot perform any action
        # until the bundle is back in draft or in preview.
        return []

    @transaction.atomic
    def unlock(self, task_state: TaskState, user: User) -> Self:
        workflow_state = task_state.workflow_state

        # Cancel the current state and switch to a new task
        # note: not calling workflow_state.current_task_state.cancel() as that calls workflow_state.update() without
        # next_step, which then results in a call to workflow_state.next_step() thus creating a task state for
        # Ready to publish, which we don't want
        workflow_state.current_task_state.status = task_state.STATUS_CANCELLED
        workflow_state.current_task_state.finished_at = timezone.now()
        workflow_state.current_task_state.finished_by = user
        workflow_state.current_task_state.save()

        workflow_state.current_task_state.log_state_change_action(user, "cancel")
        workflow_state.update(user=user, next_task=workflow_state.workflow.tasks.exclude(pk=task_state.task_id).first())
        return self

    @transaction.atomic
    def on_action(self, task_state: TaskState, user: User, action_name: str, **kwargs: Any) -> None:
        if action_name == "unlock":
            self.unlock(task_state, user)
        elif action_name == "locked-approve":
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

    def user_can_unlock_for_edits(self, obj: Model, user: User) -> bool:
        """A page that is 'ready to be published' in our workflow can be unlocked for edits
        if it is not in a bundle that is ready to be published.
        """
        return self.user_can_access_editor(obj, user) and not in_bundle_ready_to_be_published(obj)

    class Meta:
        verbose_name = "Ready to publish task"
        verbose_name_plural = "Ready to publish tasks"


class TaskStateSubmissionEmailNotifier(GroupApprovalTaskStateSubmissionEmailNotifier):
    """A notifier to send email updates for our submission events."""

    def can_handle(self, instance: TaskState, **kwargs: Any) -> bool:
        return isinstance(instance, self.valid_classes) and isinstance(
            instance.task.specific, GroupReviewTask | ReadyToPublishGroupTask
        )
