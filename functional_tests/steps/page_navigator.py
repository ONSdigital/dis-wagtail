# pylint: disable=not-callable
from behave import step
from behave.runner import Context
from playwright.sync_api import expect


@step("the user navigates to the admin page navigator")
def user_navigates_to_page_navigator(context: Context) -> None:
    context.page.goto(f"{context.base_url}/admin/pages/")


@step('the user navigates to the "{language}" homepage in the page navigator')
def user_navigates_to_homepage(context: Context, language: str) -> None:
    context.page.get_by_role("row", name=f"Select Sites menu Home {language}").get_by_label(
        "Explore child pages of 'Home'"
    ).click()


@step("the user has no option to create a child page")
def user_has_no_option_to_create_child_page(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add child page")).not_to_be_visible()


@step('the user has the option to create a child page under the "{page_title}" page')
def user_can_create_child_page_under_homepage(context: Context, page_title: str) -> None:
    context.page.get_by_role("link", name="Add child page").click()
    expect(context.page.get_by_role("heading", name=f"Create a page in {page_title}")).to_be_visible()
