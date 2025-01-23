from behave import then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@when("An external user navigates to the ONS beta site homepage")  # pylint: disable=not-callable
def external_user_navigates_to_beta_homepage(context: Context) -> None:
    context.page.goto(context.base_url)


@then("they can see the beta homepage")  # pylint: disable=not-callable
def user_sees_the_beta_homepage(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Home")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Welcome to the ONS Wagtail")).to_be_visible()
    expect(context.page.get_by_label("Office for National Statistics homepage")).to_be_visible()
    expect(context.page.get_by_text("This is a new service.")).to_be_visible()
    expect(context.page.get_by_text("Beta")).to_be_visible()


@then("they cannot see the breadcrumbs")
def user_does_not_sees_on_the_page(context: Context) -> None:
    expect(context.page.get_by_label("Breadcrumbs")).not_to_be_visible()
