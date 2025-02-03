from behave import then, when,  given # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect
from cms.core.tests.factories import ContactDetailsFactory


def sign_in(context: Context):
    context.page.get_by_placeholder("Enter your username").fill("admin")
    context.page.get_by_placeholder("Enter password").fill("changeme")
    context.page.get_by_role("button", name="Sign in").click()

def set_up_test_data(context: Context):
    sign_in(context)
    create_theme_page(context)
    create_topic_page(context)

    create_statistical_article(context)

    create_series_version(context,
                          "January 2024",
                          "2024-01-15",
                          "2024-02-15",
                          )

    create_series_version(context,
                          "February 2024",
                          "2024-02-15",
                          "2024-03-15",
                          )


def create_series_version(context, version: str, rel_date: str, next_rel_date: str):
    context.page.get_by_label("Add a child page to '").click()
    context.page.get_by_placeholder("Page title*").fill(version)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill(version + "Summary")
    context.page.get_by_label("Section heading*").fill(version + "Contents Heading")
    context.page.get_by_label("Release date").fill(rel_date)
    context.page.get_by_label("Next release date").fill(next_rel_date)
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill(
        "Contents Theme 1 Topic 1 statistics article page series")
    context.page.get_by_role("button", name="Publish").click()


def create_statistical_article(context):
    context.page.get_by_label("Add a child page to 'Test").click()
    context.page.get_by_placeholder("Page title*").fill("Statistical Series Title Page")
    context.page.get_by_role("button", name="Publish").click()


def create_topic_page(context):
    context.page.get_by_label("Add a child page to 'Test").click()
    context.page.get_by_placeholder("Page title*").fill("Test Topic Page 1 Title")
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Test Topic Page 1 Summary")
    context.page.get_by_role("button", name="Publish").click()


def create_theme_page(context):
    context.page.get_by_label("Add child page").click()
    context.page.get_by_role("link", name="Theme page . A theme page,").click()
    context.page.get_by_placeholder("Page title*").fill("Test Theme Page Title 1")
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Test Theme Page Title 1 Summary")
    context.page.get_by_role("button", name="Publish").click()


def navigate_to_release_page(context: Context):





    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()




@given("a previous_releases_page_exists")
def(create_theme_page)
def create_previous_release_page(context: Context):


@when("An external user navigates to the ONS previous releases page")  # pylint: disable=not-callable
def external_user_navigates_to_previous_releases(context: Context) -> None:

    # context.page.get_by_text("Home Theme 1 Topic 1 Article for theme 1 topic 1 series page Previous Releases").click(modifiers=["Alt"])

@then("they can see the previous releases page")  # pylint: disable=not-callable
def user_sees_the_previous_releases(context: Context) -> None:
    expect(context.page.get_by_label("Breadcrumbs")).to_be_visible()


