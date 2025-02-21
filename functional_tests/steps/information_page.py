from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@step("the user creates an information page as a child of the home page")
def user_creates_information_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Edit 'Home'").click()
    context.page.get_by_role("button", name="Actions", exact=True).click()
    context.page.get_by_role("link", name="Add a child page to 'Home'").click()
    context.page.get_by_role("link", name="Information page", exact=True).click()


@when("the user adds content to the new information page")
def user_adds_info_page_contents(context: Context) -> None:
    context.page.get_by_placeholder("Page title*").fill(" Test Info Page")

    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My test information page")

    context.page.get_by_role("textbox", name="Last updated").fill("2024-01-01")
    context.page.get_by_role("textbox", name="Last updated").press("Enter")

    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("option", name="Rich text").locator("div").first.click()
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Some example rich text content")
    context.page.get_by_role("region", name="Rich text *").get_by_label("Insert a block").click()
    context.page.get_by_text("Heading 3").click()

    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.get_by_text("Equation").click()
    context.page.locator("#content-1-value").fill("$$\\sum_{i=0}^n i^2 = \\frac{(n^2+n)(2n+1)}{6}$$")

    context.page.get_by_role("button", name="Add related pages").click()
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("cell", name="Home", exact=True).get_by_role("link").click()


@then("the new information page with the added content is displayed")
def check_new_information_is_displayed_with_content(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Test Info Page")).to_be_visible()
    expect(context.page.get_by_text("My test information page")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Last Updated: 2024-01-01")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Some example rich text content")).to_be_visible()
    expect(context.page.get_by_text("n∑i=0i2=(n2+n)(2n+1)")).to_be_visible()
    expect(context.page.get_by_role("navigation", name="Related content").get_by_role("listitem")).to_be_visible()
