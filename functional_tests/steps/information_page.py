from behave import then, when  # pylint: disable=E0611
from behave.runner import Context
from playwright.sync_api import expect


@when("the user navigates to the pages menu")
def user_navigates_to_pages_menu(context: Context) -> None:
    """User navigates to the pages menu."""
    context.page.get_by_role("link", name="2 Pages created in Office for").click()


@when("the user clicks add child page and chooses information page type")
def user_adds_information_page(context: Context) -> None:
    """User adds new information page."""
    context.page.get_by_label("Add child page").click()
    context.page.locator("li").filter(has_text="Information page Pages using").click()
    context.page.get_by_role("link", name="Information page", exact=True).click()


@when("the user adds content to the new information page")
def user_adds_info_page_contents(context: Context) -> None:
    """User adds content to the new information page."""
    context.page.get_by_placeholder("Page title*").fill(" Test Info Page")

    context.page.get_by_role("textbox", name="Summary*").fill("My test information page")

    context.page.get_by_role("textbox", name="Last updated").fill("2024-01-01")

    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("option", name="Rich text").locator("div").first.click()
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Some example rich text content")
    context.page.get_by_label("Insert a block").click()
    context.page.get_by_text("Heading 3").click()

    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.get_by_text("Equation").click()
    context.page.locator("#content-1-value").fill("$$\\sum_{i=0}^n i^2 = \\frac{(n^2+n)(2n+1)}{6}$$")

    context.page.get_by_role("button", name="Add related pages").click()
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("cell", name="Home", exact=True).get_by_role("link").click()


@when("the user clicks publish page")
def user_clicks_publish_page(context: Context) -> None:
    """User clicks publish page."""
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


@when('the user clicks "View Live" on the publish confirmation banner')
def user_clicks_view_live_on_publish_confirmation_banner(context: Context) -> None:
    """User clicks "View Live" on the publish confirmation banner."""
    expect(context.page.get_by_text("Page 'Test Info Page' created and published.")).to_be_visible()
    context.page.get_by_role("link", name="View live").click()


@then("the new information page with the added content is displayed")
def check_new_information_is_displayed_with_content(context: Context) -> None:
    """Checks the new information page with the added content is displayed."""
    expect(context.page.get_by_text("Test Info Page")).to_be_visible()
    expect(context.page.get_by_text("My test information page")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Last Updated: 2024-01-01")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Some example rich text content")).to_be_visible()
    expect(context.page.get_by_text("n∑i=0i2=(n2+n)(2n+1)")).to_be_visible()
    expect(context.page.get_by_role("navigation", name="Related content").get_by_role("listitem")).to_be_visible()
