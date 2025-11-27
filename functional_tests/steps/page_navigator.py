from behave import step  # pylint: disable=no-name-in-module
from playwright.sync_api import expect


@step("the user navigates to the admin page navigator")
def user_navigates_to_page_navigator(context):
    context.page.goto(f"{context.base_url}/admin/pages/")


@step('the user navigates to the "{language}" homepage in the page navigator')
def user_navigates_to_homepage(context, language):
    context.page.get_by_role("row", name=f"Select Sites menu Home {language}").get_by_label(
        "Explore child pages of 'Home'"
    ).click()


@step("the user has no option to create a child page")
def user_has_no_option_to_create_child_page(context):
    expect(context.page.get_by_role("link", name="Add child page")).not_to_be_visible()
