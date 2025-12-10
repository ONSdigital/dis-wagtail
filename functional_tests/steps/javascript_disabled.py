# pylint: disable=not-callable
from behave import given, then
from behave.runner import Context
from playwright.sync_api import expect


@given("the user has Javascript disabled")
def the_user_has_javascript_disabled(
    context: Context,  # pylint: disable=unused-argument
) -> None:
    # This step just exists for scenario readability.
    # The actual disabling of JavaScript is done in the before_scenario step
    # when the scenario is tagged with @no_javascript.
    pass


@given("the user has Javascript enabled")
def the_user_has_javascript_enabled(
    context: Context,  # pylint: disable=unused-argument
) -> None:
    # This step just exists for scenario readability.
    # JavaScript is enabled by default, so no action is needed.
    pass


@then("the user can see the equation fallback")
def the_user_can_see_the_equation_fallback(context: Context) -> None:
    # Article created in a_statistical_article_page_with_equations_exists()
    url = context.statistical_article_page.url
    context.page.goto(f"{context.base_url}{url}")
    expect(context.page.locator("#svgfallback")).to_be_visible()


@then("the user cannot see the equation fallback")
def the_user_cannot_see_the_equation_fallback(context: Context) -> None:
    url = context.statistical_article_page.url
    context.page.goto(f"{context.base_url}{url}")
    expect(context.page.locator("#svgfallback")).not_to_be_visible()
