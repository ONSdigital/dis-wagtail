from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wagtail.models import WorkflowState

    from cms.users.models import User


def finish_workflow_and_publish(workflow_state: WorkflowState, user: User | None = None) -> None:
    # imported inline to prevent circular imports due to earlier inclusion
    from cms.workflows.models import ReadyToPublishGroupTask  # pylint: disable=import-outside-toplevel

    if workflow_state.is_at_final_task and isinstance(
        workflow_state.current_task_state.task.specific, ReadyToPublishGroupTask
    ):
        # we got to this point through a number of checks. We can skip the "can publish"
        # in PublishPageRevisionAction.check()
        workflow_state.content_object.get_latest_revision().publish(user=user, skip_permission_checks=True)
    else:
        workflow_state.content_object.get_latest_revision().publish(user=user)
