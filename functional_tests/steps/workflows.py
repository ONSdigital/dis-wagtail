# pylint: disable=not-callable
from datetime import timedelta
from typing import Literal

from behave import step, then
from behave.runner import Context
from django.utils import timezone
from playwright.sync_api import expect

from cms.workflows.tests.utils import (
    mark_page_as_ready_for_review,
    mark_page_as_ready_to_publish,
    progress_page_workflow,
)
from functional_tests.step_helpers.users import create_user
from functional_tests.step_helpers.utils import get_page_from_context, lock_page
from functional_tests.steps.cms_login import a_user_is_logged_in
from functional_tests.steps.page_editor import (
    click_the_given_button,
    the_user_edits_a_page,
    user_clicks_action_menu_toggle,
)


@step('the {page_str} page is "{workflow_stage}"')
def the_given_page_is_in_workflow_stage(
    context: Context, page_str: str, workflow_stage: Literal["in preview", "ready to publish"]
) -> None:
    the_page = get_page_from_context(context, page_str)
    if workflow_stage.lower() == "in preview":
        mark_page_as_ready_for_review(the_page)
    elif workflow_stage.lower() == "ready to publish":
        if not the_page.current_workflow_state:
            mark_page_as_ready_to_publish(the_page)
        else:
            progress_page_workflow(the_page.current_workflow_state)
    elif workflow_stage.lower() == "published":
        the_page.save_revision().publish()


@step('the {page_str} scheduled page is at "{workflow_stage}"')
def the_given_scheduled_page_is_in_workflow_stage(
    context: Context, page_str: str, workflow_stage: Literal["in preview", "ready to publish"]
) -> None:
    the_page = get_page_from_context(context, page_str)
    the_page.go_live_at = timezone.now() + timedelta(days=1)
    the_page.save_revision()

    the_given_page_is_in_workflow_stage(context, page_str, workflow_stage)


@step("the user is the last {page_str} page editor")
def the_user_is_the_last_page_editor(context: Context, page_str: str) -> None:
    the_page = get_page_from_context(context, page_str)
    the_page.save_revision(user=context.user_data["user"])


@step("the {page_str} page is locked by another user")
def the_page_was_locked_by_another_user(context: Context, page_str: str) -> None:
    the_page = get_page_from_context(context, page_str)
    another_user_data = create_user("admin")
    lock_page(the_page, another_user_data["user"])


@step("the {page_str} page is locked by a {user_type}")
def the_page_was_locked_by_the_user(context: Context, page_str: str, user_type: str) -> None:
    the_page = get_page_from_context(context, page_str)
    context.user_data = create_user(user_type)

    lock_page(the_page, context.user_data["user"])


@then('the "{button_label}" button is {enabled_status}')
def the_given_button_is_enabled(
    context: Context, button_label: str, enabled_status: Literal["enabled", "disabled"]
) -> None:
    is_enabled: bool = enabled_status == "enabled"
    expect(context.page.get_by_role("button", name=button_label, exact=True)).to_be_enabled(
        enabled=is_enabled, timeout=500
    )


@step('the "{button_label}" button {exists}')
def the_given_button_is_present(
    context: Context, button_label: str, exists: Literal["exists", "does not exist"]
) -> None:
    count = 1 if exists == "exists" else 0
    expect(context.page.get_by_role("button", name=button_label, exact=True)).to_have_count(count)


@then('the "{link_label}" link {exists}')
def the_given_link_is_present(context: Context, link_label: str, exists: Literal["exists", "does not exist"]) -> None:
    count = 1 if exists == "exists" else 0
    expect(context.page.get_by_role("link", name=link_label, exact=True)).to_have_count(count)


@then('the "{text}" text {displayed}')
def the_given_text_is_present(
    context: Context, text: str, displayed: Literal["is displayed", "is not displayed"]
) -> None:
    locator = context.page.get_by_role("status").get_by_text(text)
    if displayed == "is displayed":
        expect(locator).to_be_visible()
    else:
        expect(locator).not_to_be_visible()


@then("the user can unlock the page for editing")
def the_user_can_unlock_the_workflow(context: Context):
    context.page.get_by_role("link", name="Unlock editing", exact=True).click()
    context.page.get_by_role("button", name="Yes, unlock it", exact=True).click()

    context.page.get_by_role("button", name="Toggle status").click()
    expect(context.page.get_by_role("complementary", name="status")).to_contain_text("Sent to In Preview now")
    expect(context.page.get_by_role("link", name="Page locked", exact=True)).to_have_count(0)


@step("the {page_str} page goes through the publishing steps with {user} as user and {approver} as reviewer")
def the_page_goes_through_the_publishing_steps(context: Context, page_str: str, user: str, approver: str) -> None:
    user_clicks_action_menu_toggle(context)
    click_the_given_button(context, "Submit to Release review")
    a_user_is_logged_in(context, approver)
    the_user_edits_a_page(context, page_str)
    user_clicks_action_menu_toggle(context)
    click_the_given_button(context, "Approve")
    a_user_is_logged_in(context, user)
    the_user_edits_a_page(context, page_str)
    user_clicks_action_menu_toggle(context)
    click_the_given_button(context, "Publish")
