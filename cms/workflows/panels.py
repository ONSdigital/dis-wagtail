from typing import TYPE_CHECKING

from django.conf import settings
from laces.components import Component
from wagtail.admin.views.home import WorkflowObjectsToModeratePanel
from wagtail.models import Page, TaskState

from cms.workflows.models import ReadyToPublishGroupTask

if TYPE_CHECKING:
    from laces.typing import RenderContext


class ONSWorkflowObjectsToModeratePanel(WorkflowObjectsToModeratePanel):
    order = 205

    def get_context_data(self, parent_context: dict | None = None) -> RenderContext | None:
        context = super().get_context_data(parent_context)

        filtered_states = []
        for state in context["states"]:
            obj = state["obj"]
            if obj.current_workflow_task and isinstance(obj.current_workflow_task, ReadyToPublishGroupTask):
                continue
            filtered_states.append(state)

        context["states"] = filtered_states

        return context


class PagesReadyToBePublishedManuallyPanel(Component):
    name = "pages_ready_to_publish"
    order = 206
    template_name = "workflows/panels/pages_ready_to_publish.html"

    def get_context_data(self, parent_context: RenderContext | None = None) -> RenderContext | None:
        # note: Wagtail passes the request in the context. Should it stop, we want this to error
        request = parent_context["request"]  # type: ignore[index]
        context = super().get_context_data(parent_context)
        context["items"] = []
        context["request"] = request
        context["csrf_token"] = parent_context["csrf_token"]  # type: ignore[index]

        if not getattr(settings, "WAGTAIL_WORKFLOW_ENABLED", True):
            return context

        states = (
            TaskState.objects.reviewable_by(request.user)
            .filter(
                task__content_type_id=ReadyToPublishGroupTask().content_type_id,
                revision__base_content_type__model=Page._meta.model_name.lower(),
                revision__base_content_type__app_label=Page._meta.app_label.lower(),
            )
            .select_related(
                "revision",
                "revision__user",
                "workflow_state",
                "workflow_state__workflow",
            )
            .prefetch_related(
                "revision__content_object",
                "revision__content_object__latest_revision",
            )
            .order_by("-started_at")[:10]
        )

        for state in states:
            # Skip task states where the revision's GenericForeignKey points to
            # a nonexistent object. This can happen if the model does not define
            # a GenericRelation to WorkflowState and/or Revision and the instance
            # is deleted.
            if not (page := state.revision.content_object):
                continue

            context["items"].append(
                {
                    "page": page,
                    "revision": state.revision,
                    "task_state": state,
                    "actions": state.task.specific.get_actions(page, request.user),
                }
            )

        return context
