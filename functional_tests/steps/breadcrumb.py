# pylint: disable=not-callable
from behave import then
from behave.runner import Context
from playwright.sync_api import expect


@then("they cannot see the breadcrumbs")
def user_does_not_see_breadcrumbs_on_the_page(context: Context) -> None:
    expect(context.page.get_by_label("Breadcrumbs")).not_to_be_visible()


@then("the user can see the breadcrumbs")
def user_does_see_breadcrumbs_on_the_page(context: Context) -> None:
    expect(context.page.get_by_label("Breadcrumbs")).to_be_visible()
