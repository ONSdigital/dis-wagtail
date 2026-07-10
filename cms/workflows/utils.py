from typing import TYPE_CHECKING

from .models import GroupReviewTask, ReadyToPublishGroupTask

if TYPE_CHECKING:
    from wagtail.models import Page


def is_page_in_workflow(page: Page) -> bool:
    """Returns True if the page is currently in one of our custom workflow tasks (In Preview or Ready to Publish)."""
    return page.current_workflow_task and isinstance(
        page.current_workflow_task, GroupReviewTask | ReadyToPublishGroupTask
    )


def is_page_ready_to_preview(page: Page) -> bool:
    # workflow_state = page.current_workflow_state
    #
    # return workflow_state and isinstance(
    #     workflow_state.current_task_state.task.specific, GroupReviewTask | ReadyToPublishGroupTask
    # )
    return True


def is_page_ready_to_publish(page: Page) -> bool:
    return page.current_workflow_task and isinstance(page.current_workflow_task, ReadyToPublishGroupTask)
