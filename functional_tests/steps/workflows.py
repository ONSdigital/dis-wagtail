# pylint: disable=not-callable
from typing import Literal

from behave import step, then
from behave.runner import Context
from playwright.sync_api import expect

from cms.workflows.tests.utils import mark_page_as_ready_for_review, mark_page_as_ready_to_publish


@step('the {page} page is "{workflow_stage}"')
def the_given_page_is_in_workflow_stage(
    context: Context, page: str, workflow_stage: Literal["in preview", "ready to publish"]
) -> None:
    the_page_attr = page.lower().replace(" ", "_")
    if not the_page_attr.endswith("_page"):
        the_page_attr += "_page"
    the_page = getattr(context, the_page_attr)
    if workflow_stage == "in preview":
        mark_page_as_ready_for_review(the_page)
    elif workflow_stage == "ready to publish":
        mark_page_as_ready_to_publish(the_page)


@step("the user is the last {page} page editor")
def the_user_is_the_last_page_editor(context: Context, page: str) -> None:
    the_page_attr = page.lower().replace(" ", "_")
    if not the_page_attr.endswith("_page"):
        the_page_attr += "_page"
    the_page = getattr(context, the_page_attr)
    the_page.save_revision(user=context.user_data["user"])


@then('the "{button_label}" button is {enabled_status}')
def the_given_button_is_enabled(
    context: Context, button_label: str, enabled_status: Literal["enabled", "disabled"]
) -> None:
    is_enabled: bool = enabled_status == "enabled"
    expect(context.page.get_by_role("button", name=button_label, exact=True)).to_be_enabled(
        enabled=is_enabled, timeout=500
    )


@then('the "{button_label}" button {exists}')
def the_given_button_is_present(
    context: Context, button_label: str, exists: Literal["exists", "does not exist"]
) -> None:
    count = 1 if exists == "is" else 0
    expect(context.page.get_by_role("button", name=button_label, exact=True)).to_have_count(count)
