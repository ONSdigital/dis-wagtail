# pylint: disable=not-callable
import re

from behave import step, then, when
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect
from wagtail.models import Locale

from cms.themes.models import ThemeIndexPage
from cms.themes.tests.factories import ThemeIndexPageFactory
from functional_tests.step_helpers.utils import get_page_from_context

RE_UNLOCKED = re.compile(r"Page '.*' is now unlocked\.")


@when("the user clicks the action button toggle")
def user_clicks_action_menu_toggle(context: Context) -> None:
    context.page.get_by_role("button", name="More actions").click()


@step('the user clicks "Publish"')
@when("publishes the page")
def user_clicks_publish(context: Context) -> None:
    # Focus on the Status button to prevent overlap when trying to click the Publish button
    context.page.locator('[data-w-tooltip-content-value="Status"]').focus()
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


@when('the user clicks "View Live" on the publish confirmation banner')
def user_clicks_view_live_on_publish_confirmation_banner(context: Context) -> None:
    context.page.get_by_role("link", name="View live").click()


@step('the user clicks the "{button_text}" button')
def click_the_given_button(context: Context, button_text: str) -> None:
    # Focus on the Status button to prevent overlap when trying to click the button
    context.page.locator('[data-w-tooltip-content-value="Status"]').focus()
    if button_text in ("Save Draft", "Preview"):
        # add a small delay to allow any client-side JS to initialise.
        context.page.wait_for_timeout(500)
    context.page.get_by_role("button", name=button_text).click()


@step('the user opens the preview in a new tab, using the "{preview_mode}" preview mode')
def open_new_preview_tab_with_preview_mode(context: Context, preview_mode: str) -> None:
    click_the_given_button(context, "Preview")
    context.page.get_by_label("Preview mode").select_option(preview_mode)

    with context.page.expect_popup() as preview_tab:
        context.page.get_by_role("link", name="Preview in new tab").click()
    # closes context.page (admin page)
    context.page.close()
    # assigns context.page to the pop up tab
    context.page = preview_tab.value


@when("the user edits the {page} page")
def the_user_edits_a_page(context: Context, page: str) -> None:
    the_page = page.lower().replace(" ", "_")

    if not the_page.endswith("_page"):
        the_page += "_page"
    edit_url = reverse("wagtailadmin_pages:edit", args=[getattr(context, the_page).pk])
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the {page} page has a Welsh translation")
def the_page_has_a_welsh_alias(context: Context, page: str) -> None:
    the_page_str = page.lower().replace(" ", "_")
    if not the_page_str.endswith("_page"):
        the_page_str += "_page"
    welsh_locale = Locale.objects.get(language_code="cy")
    the_page = getattr(context, the_page_str)
    try:
        the_page.get_translation(welsh_locale)
    except the_page.DoesNotExist:
        # If a translation doesn't already exist, create one
        the_page.copy_for_translation(welsh_locale, copy_parents=True)


@when("the user tries to create a new theme page")
def user_tries_to_create_new_theme_page(context: Context) -> None:
    if not hasattr(context, "theme_index_page"):
        try:
            theme_index_page = ThemeIndexPage.objects.get()
        except ThemeIndexPage.DoesNotExist:
            theme_index_page = ThemeIndexPageFactory(title="Browse")
        context.theme_index_page = theme_index_page

    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").first.click()
    context.page.get_by_role("link", name=context.theme_index_page.title, exact=True).click()
    context.page.get_by_role("link", name="Add child page").click()


@when("the user tries to create a new topic page")
def user_tries_to_create_new_topic_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home English", exact=True).click()
    context.page.get_by_role("link", name="Add child page").click()
    context.page.get_by_role("link", name="Topic page . A specific topic").click()


@when("the user tries to create a new information page")
def user_tries_to_create_new_information_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home English", exact=True).click()
    context.page.get_by_role("link", name="Add child page").click()
    context.page.get_by_role("link", name="Information page", exact=True).click()


@when("the user fills in the required topic page content")
@when("the user fills in the required theme page content")
def user_fills_required_topic_theme_page_content(context: Context) -> None:
    context.page_title = "Test Title"
    context.page.get_by_role("textbox", name="Title*").fill(context.page_title)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Test Summary")


@then("the user can successfully publish the page")
def the_user_can_successfully_publish_the_page(context: Context) -> None:
    publish_page(context)
    expect(context.page.get_by_text(f"Page '{context.page_title}' created and published")).to_be_visible()


def publish_page(context: Context) -> None:
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


def publish_snippet(context: Context) -> None:  # Create an alias so it reads better
    publish_page(context)


@when("the user navigates to the page history menu")
def user_navigates_to_the_history_menu(context: Context) -> None:
    context.page.get_by_role("link", name="History").click()


@then("the saved draft version is visible")
def saved_draft_version_is_visible(context: Context) -> None:
    expect(context.page.get_by_role("button", name="Just now").first).to_be_visible()
    expect(context.page.get_by_text("Draft saved")).to_be_visible()


@when("the user refreshes the page")
def the_user_refreshes_the_page(context: Context) -> None:
    context.page.reload()


@step("the rich text toolbar is pinned")
def check_rich_text_toolbar_is_displayed_by_default(context: Context) -> None:
    expect(context.page.get_by_role("toolbar")).to_be_visible()


@when("the user unpins the rich text toolbar")
def the_user_unpins_the_rich_text_toolbar(context: Context) -> None:
    context.page.get_by_role("button", name="Unpin toolbar").click()


@then("the rich text toolbar is unpinned")
def check_rich_text_toolbar_is_unpinned(context: Context) -> None:
    expect(context.page.get_by_role("toolbar")).not_to_be_visible()


@step("the minimap is displayed")
def check_minimap_is_displayed(context: Context) -> None:
    expect(context.page.get_by_role("complementary", name="Minimap").locator("div").nth(1)).to_be_visible()


@when("the user hides the minimap")
def the_user_hides_the_minimap(context: Context) -> None:
    context.page.get_by_role("button", name="Toggle side panel").click()


@then("the minimap is hidden")
def the_minimap_is_hidden(context: Context) -> None:
    expect(context.page.get_by_role("complementary", name="Minimap").locator("div").first).not_to_be_visible()


@step("the user can save a draft version of the page")
def the_user_can_save_a_page(context: Context) -> None:
    expect(context.page.get_by_role("button", name="Save draft")).to_be_visible()


@step("the user can publish a page")
@step("the user can publish the page")
def the_user_can_publish_a_page(context: Context) -> None:
    expect(context.page.get_by_role("button", name="More actions")).to_be_visible()
    context.page.get_by_role("button", name="More actions").click()
    expect(context.page.get_by_role("button", name="Publish")).to_be_visible()


@step("the user can unlock the page")
def the_user_unlock_a_page(context: Context) -> None:
    context.page.get_by_role("button", name="Toggle status").click()
    context.page.get_by_text("Lock", exact=True).click()
    expect(context.page.get_by_text(RE_UNLOCKED)).to_be_visible()


@step("the user can lock and unlock a page")
def the_user_can_lock_and_unlock_a_page(context: Context) -> None:
    context.page.get_by_role("button", name="Toggle status").click()
    context.page.get_by_text("Lock", exact=True).click()
    expect(context.page.get_by_text(re.compile(r"'.*' was locked by you"))).to_be_visible()
    context.page.get_by_text("Lock", exact=True).click()
    expect(context.page.get_by_text(RE_UNLOCKED)).to_be_visible()


@step("the user can bulk delete the topic page and its children")
def the_user_can_bulk_delete_a_theme_page_and_its_children(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home English", exact=True).click()
    context.page.get_by_role("button", name=f"More options for '{context.topic_page.title}'").click()
    context.page.get_by_role("link", name="Delete").click()
    expect(context.page.get_by_role("link", name="This topic page is referenced")).to_be_visible()
    expect(context.page.get_by_text("Are you sure you want to")).to_be_visible()
    context.page.get_by_role("button", name="Yes, delete it").click()
    expect(context.page.get_by_text(f"Page '{context.topic_page.title}' deleted.")).to_be_visible()


@when('the user clicks "Save" to save the Snippet')
def user_saves_in_navigation_settings(context: Context) -> None:
    context.page.get_by_role("button", name="Save").click()


@when("the user clicks toggle preview")
def user_clicks_view_live(context: Context) -> None:
    context.page.get_by_role("button", name="Toggle preview").click()


@step("the user returns to editing the published page")
def user_returns_to_editing_the_published_page(context: Context) -> None:
    context.page.get_by_role("link", name="Edit").click()


@step("the user opens the page actions menu")
def user_open_page_actions_menu(context: Context) -> None:
    context.page.locator("#w-slim-header-buttons").get_by_role("button", name="Actions").click()


@step("the user has no option to copy the page")
def user_has_no_option_to_copy_page(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Copy")).not_to_be_visible()


@step("the user has the option to copy the page")
def user_has_option_to_copy_page(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Copy")).to_be_visible()


@then("the published {page_str} page is displayed")
def the_published_page_is_displayed(context: Context, page_str: str) -> None:
    the_page = get_page_from_context(context, page_str)
    # note: we don't display the summary anywhere other than the edit form, or the published page
    expect(context.page.get_by_text(the_page.summary, exact=True)).to_be_visible()
