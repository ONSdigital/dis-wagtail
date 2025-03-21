from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.navigation.tests.factories import FooterMenuFactory


@given("a footer menu exists")
def create_footer_menu(context: Context):
    context.footer_menu = FooterMenuFactory()


@step("the user creates a footer menu instance")
def user_creates_footer_menu_instance(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="add one").click()


@step("the user populates the footer menu")
def user_populates_footer_menu(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").click()
    context.page.get_by_role("textbox", name="Column title*").fill("About")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.ons.gov.uk/help/accessibility")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Accessibility")


@when("the user populates the footer menu with a page")
def user_adds_home_page(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").fill("Home page")
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("link", name="Home").click()


@then("the preview of the footer menu is displayed with the home page")
def preview_home_page(context: Context):
    # Home cannot be found
    # context.page.get_by_role("link", name="Home").click()
    expect(context.page.get_by_role("link", name="Home", exact=True)).to_be_visible()


@when("the user clicks to the preview")
def user_clicks_view_live(context: Context):
    context.page.get_by_role("button", name="Toggle preview").click()

    #'the user clicks "View Live" from the preview'
    # This opens preview in another tab which is not necessary in most cases
    # context.page.get_by_role("link", name="Preview in new tab").click()


@then("the preview of the footer menu is displayed with the populated data")
def user_previews_footer_menu(context: Context):
    # Heading and link
    expect(context.page.get_by_role("heading", name="About")).to_be_visible()
    expect(context.page.get_by_role("link", name="Accessibility")).to_be_visible()


@step('the user clicks "Publish" the footer menu')
def user_publishes_footer_menu(context: Context):
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


@then("a banner confirming changes is displayed")
def deleted_footer_menu_banner(context: Context):
    # Banner confirmation cannot be described fully
    expect(context.page.get_by_text("Footer menu 'Footer Menu'")).to_be_visible()


@when('a CMS user navigates to "Navigation settings"')
def user_navigates_to_navigation_settings(context: Context):
    context.page.get_by_role("button", name="Settings").click()
    context.page.get_by_role("link", name="Navigation settings").click()


@when('the user selects footer menu in "Navigation settings"')
def user_selects_footer_menu(context: Context):
    context.page.get_by_role("button", name="Choose footer menu").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@when('the user clicks "saves" in the "Navigation Settings"')
def user_saves_in_navigation_settings(context: Context):
    context.page.get_by_role("button", name="Save").click()


@step("the footer menu is configured")
def user_configures_footer_menu(context: Context):
    context.page.get_by_role("button", name="Choose footer menu", exact=False)
    expect(context.page.get_by_text("Navigation settings updated.")).to_be_visible()


@when("the user inserts an empty column block")
def user_inserts_empty_footer_menu_block(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()


@when("the user enters duplicate information")
def user_enters_duplicate_link(context: Context):
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.locator("#columns-1-value-title").fill("About")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill(
        "https://www.ons.gov.uk/help/accessibility"
    )
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("Accessibility")


@when("the user enters a link with no title")
def user_enters_link_with_no_title(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("www.google.com")
    context.page.locator("#columns-0-value-links-1-value-title").click()


@when("the user enters an incorrect url")
def user_enters_incorrect_url(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("wwwgcom")
    context.page.locator("#columns-0-value-links-1-value-title").click()
    context.page.locator("#columns-0-value-links-1-value-title").fill("Goggle")


@when("the user enters more than 3 columns")
def user_inserts_more_than_max_columns(context: Context):
    titles = ["Title 2", "Title 3", "Title 4"]
    links = ["www.2.com", "www.3.com", "www.4.com"]
    link_titles = ["2nd link title", "3rd link title", "4th link title"]

    for i in range(1, len(titles) + 1):
        context.page.get_by_role("button", name="Insert a block").nth(i).click()
        context.page.locator(f"#columns-{i}-value-title").fill(titles[i - 1])
        context.page.locator(f"#columns-{i}-value-links-0-value-external_url").fill(links[i - 1])
        context.page.locator(f"#columns-{i}-value-links-0-value-title").fill(link_titles[i - 1])


@when("the user adds above the maximum links")
def user_adds_above_max_links(context: Context):
    links = [
        "www.2.com",
        "www.3.com",
        "www.4.com",
        "www.5.com",
        "www.6.com",
        "www.7.com",
        "www.8.com",
        "www.9.com",
        "www.10.com",
        "www.11.com",
    ]
    link_titles = [
        "2nd link title",
        "3rd link title",
        "4th link title",
        "5th link title",
        "6th link title",
        "7th link title",
        "8th link title",
        "th link title",
        "10th link title",
        "11th link title",
    ]

    for i in range(1, len(links) + 1):
        context.page.get_by_role("button", name="Add").nth(i).click()
        context.page.locator(f"#columns-0-value-links-{i}-value-external_url").click()
        context.page.locator(f"#columns-0-value-links-{i}-value-external_url").fill(links[i - 1])
        context.page.locator(f"#columns-0-value-links-{i}-value-title").click()
        context.page.locator(f"#columns-0-value-links-{i}-value-title").fill(link_titles[i - 1])


@then("an error message confirming the footer cannot be saved is displayed")
def footer_menu_not_saved(context: Context):
    # Banner confirmation cannot be described fully
    expect(context.page.get_by_text("The footer menu could not be")).to_be_visible()


@then("an error message and maximum number of column notification is displayed")
def max_column_error_in_footer_menu(context: Context):
    footer_menu_not_saved(context)
    expect(context.page.get_by_text("The maximum number of items is")).to_be_visible()


@step("the user navigates to edit the footer menu")
def user_navigates_to_footer_menu(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@when("the user adds an additional link to a footer menu")
def user_adds_link_to_footer_menu(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("https://www.ons.gov.uk/help")
    context.page.locator("#columns-0-value-links-1-value-title").click()
    context.page.locator("#columns-0-value-links-1-value-title").fill("More")


@then("the preview of the footer menu is displayed with the additional link")
def preview_add_to_footer_menu(context: Context):
    # Heading and link - link not found
    expect(context.page.get_by_role("link", name="More")).to_be_visible()
    # expect(context.page.get_by_text("More")).to_be_visible()
    # expect(context.page.get_by_role("link")).to_be_visible()


@when("the user deletes the additional link")
def user_deletes_link(context: Context):
    context.page.get_by_role("button", name="Delete").nth(1).click()


@then("the preview does not show the deleted link")
def preview_deleted_link(context: Context):
    user_clicks_view_live(context)
    expect(context.page.get_by_role("link", name="More")).not_to_be_visible()


@when("the user edits data on a pre existing footer menu")
def user_edits_footer_menu(context: Context):
    context.page.locator("#columns-0-value-title").click()
    context.page.locator("#columns-0-value-title").fill("")
    context.page.locator("#columns-0-value-title").fill("New Title")
    context.page.locator("#columns-0-value-links-0-value-external_url").click()
    context.page.locator("#columns-0-value-links-0-value-external_url").fill("http://www.newlink.com")
    context.page.locator("#columns-0-value-links-0-value-title").click()
    context.page.locator("#columns-0-value-links-0-value-title").fill("")
    context.page.locator("#columns-0-value-links-0-value-title").fill("New link title")


@then("the preview of the footer menu is displayed with the edited data")
def preview_edited_footer_menu(context: Context):
    # Heading and link - link not found
    expect(context.page.get_by_role("heading", name="New Title")).to_be_visible()
    expect(context.page.get_by_role("link", name="New link Title")).to_be_visible()


@step("the user adds an additional column and link")
def user_adds_new_column(context: Context):
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.locator("#columns-1-value-title").fill("Column 2")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill("https://www.example.com")
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("Example")


@then("the preview will show the new column is added")
def preview_new_column(context: Context):
    # Heading and link
    expect(context.page.get_by_role("heading", name="Column 2")).to_be_visible()
    expect(context.page.get_by_role("link", name="Example")).to_be_visible()


@when("the user deletes a column")
def deletes_column(context: Context):
    context.page.get_by_role("button", name="Delete").nth(2).click()


@then("the preview will not show the deleted column")
def preview_deleted_column(context: Context):
    # Heading and link
    expect(context.page.get_by_role("heading", name="Column 2")).not_to_be_visible()
    expect(context.page.get_by_role("link", name="Example")).not_to_be_visible()


@when("user deletes the footer menu")
def user_deletes_footer_menu(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("button", name="More options for 'Footer Menu'").click()
    context.page.get_by_role("link", name="Delete 'Footer Menu'").click()
    context.page.get_by_role("button", name="Yes, delete").click()


@step("a populated footer menu has been created")
def create_original_footer_menu(context: Context):
    user_creates_footer_menu_instance(context)
    # user_populates_footer_menu(context)
    user_adds_home_page(context)


@when("the user configures the footer menu in navigation settings")
def configure_footer_menu_in_navigation_settings(context: Context):
    user_navigates_to_navigation_settings(context)
    user_selects_footer_menu(context)
    user_saves_in_navigation_settings(context)


@then("user navigates to home page")
def user_clicks_home_button(context: Context):
    context.page.get_by_role("link", name="Office for National Statistics homepage").click()


@then("the user navigates to the home page to see changes")
def navigates_to_home_page(context: Context):
    # Try and open new tab
    # Does not work (New tab cannot be opened)
    # context.page1 = context.new_page()
    # context.page1.goto("http://0.0.0.0:8000/")
    # user_previews_footer_menu(context)

    # Go to footer menu then open it's preview tab
    user_navigates_to_footer_menu(context)
    user_clicks_view_live(context)
    context.page.get_by_role("link", name="Preview in new tab").click()

    # Try and access by clicking home button
    # context.page.get_by_role("link", name="Office for National Statistics homepage").click()
    # expect(context.page.get_by_role("heading")).to_be_visible()

    # access by accessing footer menu, and click home link from the footer
    # waiting for get_by_role("link", name="Home")
    context.page.get_by_role("link", name="Home").click()
    preview_home_page(context)
