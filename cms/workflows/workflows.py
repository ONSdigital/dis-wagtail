from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wagtail.models import WorkflowState

    from cms.users.models import User


def finish_workflow_and_publish(workflow_state: WorkflowState, user: User | None = None) -> None:
    """This function will be called when the workflow finishes.

    It is configured via the WAGTAIL_FINISH_WORKFLOW_ACTION setting, and it expands the core
    logic to take into account our locked ReadyToPublishGroupTask workflow task and BasePagePermissionTester.can_publish

    See https://docs.wagtail.org/en/stable/reference/settings.html#wagtail-finish-workflow-action
    and https://github.com/wagtail/wagtail/blob/e02b1df820b8c761c18678b9fb88486bd773f5de/wagtail/workflows.py#L25-L27
    """
    # imported inline to prevent circular imports due to earlier inclusion
    from cms.workflows.models import ReadyToPublishGroupTask  # pylint: disable=import-outside-toplevel

    # We can skip the "can publish" PublishPageRevisionAction.check() if we got here from a
    # ReadyToPublishGroupTask as we have additional checks before the workflow finishes.
    should_skip_permission_checks = workflow_state.is_at_final_task and isinstance(
        workflow_state.current_task_state.task.specific,
        ReadyToPublishGroupTask,
    )

    workflow_state.content_object.get_latest_revision().publish(
        user=user,
        skip_permission_checks=should_skip_permission_checks,
    )
