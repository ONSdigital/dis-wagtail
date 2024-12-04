from behave import then, when  # pylint: disable=E0611
from behave.runner import Context
from playwright.sync_api import expect


@when("the user navigates to the release calendar page")
def navigate_to_release_page(context: Context):
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


@when('clicks "add child page" to create a new draft release page')
def click_add_child_page(context: Context):
    context.page.get_by_label("Add child page").click()


@when('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str):
    context.page.get_by_label("Status*").select_option(page_status.upper())


@when("enters some example content on the page")
def enter_example_release_content(context: Context):
    context.page.get_by_placeholder("Page title*").fill("My Release")

    context.page.get_by_label("Release date", exact=True).fill("2024-12-25")
    context.page.get_by_label("Release date", exact=True).press("Enter")

    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    context.page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("region", name="Release content").get_by_label("Title*").fill("My Example Content")

    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_label("Explore").click()
    context.page.get_by_role("link", name="Release calendar").click()

    context.page.get_by_role("button", name="Choose contact details").click()
    context.page.get_by_role("link", name=context.contact_details_snippet.name).click()

    context.page.get_by_label("Accredited Official Statistics").check()


@then("the new published release page with the example content is displayed")
def check_provisional_release_page_content(context: Context):
    expect(context.page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(context.page.get_by_role("heading", name="My Release UK Statistics").locator("span")).to_be_visible()
    expect(context.page.get_by_role("heading", name="My Example Content")).to_be_visible()
    expect(context.page.get_by_role("link", name="Release calendar")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(context.page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(context.page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()
    expect(context.page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()
