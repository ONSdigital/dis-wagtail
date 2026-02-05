from typing import TYPE_CHECKING

from wagtail.models import Workflow

if TYPE_CHECKING:
    from wagtail.models import Page, WorkflowState

    from cms.users.models import User


def progress_page_workflow(workflow_state: WorkflowState) -> None:
    task_state = workflow_state.current_task_state
    task_state.task.on_action(task_state, user=None, action_name="approve")


def mark_page_as_ready_for_review(page: Page, user: User | None = None) -> WorkflowState:
    page.save_revision(user=user)
    workflow = Workflow.objects.get(name="Release review")
    # start the workflow
    return workflow.start(page, user=user)


def mark_page_as_ready_to_publish(page: Page, user: User | None = None) -> WorkflowState:
    page.save_revision(user=user)
    workflow = Workflow.objects.get(name="Release review")
    # start the workflow
    workflow_state = workflow.start(page, user=user)

    # approve the first task ("review" / "preview")
    progress_page_workflow(workflow_state)

    return workflow_state
