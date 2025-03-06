from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context


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
    context.page.get_by_role("textbox", name="Column title*").fill("")
    context.page.get_by_role("textbox", name="Column title*").press("CapsLock")
    context.page.get_by_role("textbox", name="Column title*").fill("About")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.ons.gov.uk/help/accessibility")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).press("CapsLock")
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Accessibility")


@when('the user clicks "save draft"')
def user_clicks_publish_menu(context: Context):
    context.page.get_by_role("button", name="Save draft").click()


@when('the user clicks "View Live"')
def user_clicks_view_live(context: Context):
    context.page.get_by_role("button", name="Toggle preview").click()
    with context.page.expect_popup():
        context.page.get_by_role("link", name="Preview in new tab").click()


@then("the preview of the footer menu is displayed with the populated data")
def preview_footer_menu(context: Context):
    context.page()


# @given("pre-populated footer menu exists")
# def step_impl(context):


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
