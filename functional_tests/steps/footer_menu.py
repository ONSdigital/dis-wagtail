from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@step("the user creates a footer menu")
def user_creates_footer_menu(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="add one").click()


@when("the user populates the footer menu")
def user_populates_footer_menu(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").click()
    context.page.get_by_role("textbox", name="Column title*").press("CapsLock")
    context.page.get_by_role("textbox", name="Column title*").fill("About")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.ons.gov.uk/help/accessibility")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).press("CapsLock")
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Accessibility")


@when('the user clicks "View Live"')
def user_clicks_view_live(context: Context):
    context.page.get_by_role("button", name="Toggle preview").click()
    with context.page.expect_popup():
        context.page.get_by_role("link", name="Preview in new tab").click()


@then("the preview of the footer menu is displayed with the populated data")
def preview_footer_menu(context: Context):
    expect(context.page.get_by_role("heading", name="About")).to_be_visible()
    expect(context.page.get_by_role("link", name="Accessibility")).to_be_visible()


@when("the user inputs empty footer")
def empty_footer_menu(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("button", name="Save draft").click()


@then("an error message is presented")
def error_message_footer_menu(context: Context):
    expect(context.page.get_by_text("The footer menu could not be")).to_be_visible()
    expect(context.page.get_by_text("This field is required.")).to_be_visible()
    expect(context.page.get_by_text("Missing required fields")).to_be_visible()


@when("a pre-populated footer menu exists")
def populated_footer(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@when("a footer menu exists")
def footer_menu_exists(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@step("no footer menu is selected")
def no_footer_menu_assigned(context: Context):
    context.page.get_by_role("button", name="Choose footer menu", exact=False)


@when('a CMS user navigates to "Navigation settings"')
def navigation_settings(context: Context):
    context.page.get_by_role("button", name="Settings").click()
    context.page.get_by_role("link", name="Navigation settings").click()


@when("chooses footer menu")
def footer_menu_nav_set(context: Context):
    context.page.get_by_role("button", name="Choose footer menu").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@when('clicks "saves"')
def click_save(context: Context):
    context.page.get_by_role("button", name="Save").click()


@step("footer menu is assigned")
def assign_footer_menu(context: Context):
    context.page.get_by_role("button", name="Choose footer menu", exact=False)


@when("the user edits a footer menu")
def edit_footer_menu(context: Context):
    context.page.get_by_role("textbox", name="Column title*").click()
    context.page.get_by_role("textbox", name="Column title*").fill("More")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.ons.gov.uk")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Site")


@when("the preview of the footer menu is displayed with the edited data")
def edited_footer_menu(context: Context):
    expect(context.page.get_by_role("link", name="Site")).to_be_visible()


# @when("the user edits a footer menu")
# def step_impl(context):
#     raise NotImplementedError(u'STEP: When the user edits a footer menu')


# @then("the preview of the footer menu is displayed with the edited data")
# def step_impl(context):
#     raise NotImplementedError(u'STEP: Then the preview of the footer menu is displayed with the edited data')


# @when("user adds a duplicate link")
# def step_impl(context):
#     raise NotImplementedError(u'STEP: When user adds a duplicate link')


# @then("an error message is displayed next to the duplicated link field")
# def step_impl(context):
#     raise NotImplementedError(u'STEP: Then an error message is displayed next to the duplicated link field')
