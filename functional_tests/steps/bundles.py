from datetime import datetime, time, timedelta

from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.core.custom_date_format import ons_date_format
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory
from functional_tests.steps.release_page import click_add_child_page, navigate_to_release_calendar_page

tomorrow = timezone.now() + timedelta(days=1)


@step("a bundle has been created")
def a_bundle_has_been_created(context: Context) -> None:
    context.bundle = BundleFactory()


@step("is ready for review")
def the_bundle_is_ready_for_review(context: Context) -> None:
    context.bundle.status = BundleStatus.IN_REVIEW
    context.bundle.save(update_fields=["status"])


@step("has a preview team")
def a_bundle_has_a_preview_team(context: Context) -> None:
    context.team = Team.objects.create(identifier="preview-team", name="Preview team")
    BundleTeam.objects.create(parent=context.bundle, team=context.team)


@step("the viewer is in the preview team")
def the_viewer_is_in_the_preview_team(context: Context) -> None:
    user = context.user_data["user"]
    user.teams.add(context.team)


@step("the user navigates to the bundle creation page")
def the_user_goes_to_the_bundle_creation_page(context: Context) -> None:
    context.page.goto(context.base_url + "/admin/bundle/new/")


@step("the user opens the release calendar page chooser")
def the_user_selects_a_release_calendar(context: Context) -> None:
    context.page.get_by_role("button", name="Choose Release Calendar page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open


@step("the user opens the page chooser")
def the_user_opens_page_chooser(context: Context) -> None:
    context.page.get_by_role("button", name="Add page").click()
    context.page.wait_for_timeout(100)
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open


@step("the locale column is displayed in the chooser")
def the_locale_column_is_displayed(context: Context) -> None:
    modal = context.page.locator(".modal-body")
    modal.get_by_role("columnheader", name="Locale").is_visible()


@then("the selected datasets are displayed in the inspect view")
@then('the selected datasets are displayed in the "Data API datasets" section')
def the_selected_datasets_are_displayed(context: Context) -> None:
    context.page.get_by_role("heading", name="Dataset 1").is_visible()
    context.page.get_by_text("Looked up dataset (Edition: Example Dataset 1, Ver: 1)").is_visible()
    context.page.get_by_role("heading", name="Dataset 2").is_visible()
    context.page.get_by_text(
        "Personal well-being estimates by local authority (Edition: Example Dataset 2, Ver: 1)"
    ).is_visible()
    context.page.get_by_role("heading", name="Dataset 3").is_visible()
    context.page.get_by_text(
        "Deaths registered weekly in England and Wales by region (Edition: Example Dataset 3, Ver: 1)"
    ).is_visible()


# bundle create amend
@step("a bundle has been created with a creator")
def a_bundle_has_been_created_with_user(context: Context) -> None:
    context.bundle_creator = UserFactory()
    context.bundle = BundleFactory(created_by=context.bundle_creator)


@step("the bundle has creator removed")
def delete_bundle_creator(context: Context) -> None:
    context.bundle_creator.delete()


# bundle goto
@step("the user goes to the bundle inspect page")
def go_to_bundle_inspect(context: Context) -> None:
    context.page.goto(context.base_url + reverse("bundle:inspect", args=[context.bundle.pk]))


@step("the user clicks on the inspect link for the created bundle")
def user_clicks_on_inspect_link_for_created_bundle(context: Context) -> None:
    # This is a different approach when bundle does not exist in the context
    context.page.locator("#w-slim-header-buttons").get_by_role("button", name="Actions").click()
    context.page.get_by_role("link", name="Inspect", exact=True).click()


@step("the user goes to the bundle menu page")
def go_to_bundle_menu(context: Context) -> None:
    context.page.goto(context.base_url + reverse("bundle:index"))


# bundle Menu
@step("the bundle menu shows bundle and Added by is not empty")
def bundle_menu_contains_value(
    context: Context,
) -> None:
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle.name)
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle_creator.get_full_name())


@step("the bundle menu shows bundle and Added by is empty")
def bundle_menu_does_not_contain_value(context: Context) -> None:
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle.name)
    expect(context.page.get_by_role("table")).not_to_contain_text(context.bundle_creator.get_full_name())


@step("the user saves the bundle as draft")
def user_saves_bundle_as_draft(context: Context) -> None:
    context.page.get_by_role("button", name="Save as Draft").click()


@step("the user sets the bundle title")
def user_sets_bundle_title(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("Test Bundle")


@step("the user opens the preview for one of the selected datasets")
def user_opens_preview_for_one_of_the_selected_datasets(context: Context) -> None:
    context.page.get_by_role("link", name="Preview", exact=True).nth(0).click()


@step("the user can see the preview items dropdown")
def user_can_see_preview_items_dropdown(context: Context) -> None:
    context.page.get_by_label("Preview items").is_visible()


# bundle Inspect
@step("the user can inspect Bundle details and Created by is not empty")
def the_user_can_see_the_bundle_details_with_creator(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).to_be_visible()


@step("the user can inspect Bundle details and Created by is empty")
def bundle_inspect_show(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).not_to_be_visible()


# To test release calendar page panel
@given("a release calendar page with a future release date exists")
@given('a release calendar page with a "{status}" status and future release date exists')
def release_calendar_page_with_status_and_future_date_exists(context: Context, status: str = "Provisional") -> None:
    context.release_calendar_page = ReleaseCalendarPageFactory(
        release_date=tomorrow,
        status=status.upper(),
        notice="default notice",
    )
    context.release_calendar_page.save_revision().save()


@step('the user manually creates a future release calendar page with a "{status}" status')
def user_manually_creates_future_release_calendar(context: Context, status: str) -> None:
    navigate_to_release_calendar_page(context)
    click_add_child_page(context)
    title = "Future Release Calendar Page"
    context.page.get_by_placeholder("Page title*").fill(title)
    context.page.get_by_label("Status*").select_option(status.upper())
    formatted_date = tomorrow.strftime("%Y-%m-%d %H:%M")
    context.page.get_by_role("textbox", name="Release date*").fill(formatted_date)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    # Save the values to access later
    context.saved_release_calendar_page_details = {
        "title": title,
        "release_date_value": ons_date_format(tomorrow, "DATETIME_FORMAT"),
        "status": status,
    }


@when("the user enters a title")
def user_enters_title(context: Context) -> None:
    context.page.get_by_role("textbox", name="Name*").fill("Test Bundles")


@step("the user selects the existing release calendar page")
def user_creates_bundle_with_future_release_calendar_page(context: Context) -> None:
    try:
        title = context.release_calendar_page.title
    except AttributeError:
        title = context.saved_release_calendar_page_details["title"]

    context.page.get_by_text(title).click()


@step('the user clicks "Save as draft"')
def user_clicks_save_as_draft(context: Context) -> None:
    context.page.get_by_role("button", name="Save as draft").click()


@step("the user sees the release calendar page title, status and release date")
def user_sees_release_calendar_page_title_status_release_date(
    context: Context,
) -> None:
    expect(
        context.page.get_by_text(
            f"{context.release_calendar_page.title} ({context.release_calendar_page.status},"
            f" {context.release_calendar_page.release_date_value})"
        )
    ).to_be_visible()


@then('the user cannot see the "Cancelled" release calendar page')
def user_cannot_see_cancelled_release_calendar_page(context: Context) -> None:
    expect(context.page.get_by_text(context.release_calendar_page.title)).not_to_be_visible()


@step('the user updates the selected release calendar page\'s title, release date and sets the status to "{status}"')
def user_updates_selected_release_calendar_page_title_release_date_status(context: Context, status: str) -> None:
    day_after_tomorrow = timezone.localdate() + timedelta(days=2)

    # Set time to 10 am as using datetime.now() displayed an hour earlier than actual time for checking the updated time
    new_date = timezone.make_aware(datetime.combine(day_after_tomorrow, time(10, 0)), timezone.get_current_timezone())

    context.page.get_by_role("region", name="Scheduling").get_by_label("Actions").click()
    with context.page.expect_popup() as edit_release_calendar_page:
        context.page.get_by_role("link", name="Edit Release Calendar page").click()
    # closes original bundles edit view
    context.page.close()
    # assigns context to new release calendar page edit view
    context.page = edit_release_calendar_page.value
    # tracks original release calendar details
    context.original_date = context.saved_release_calendar_page_details["release_date_value"]
    context.original_title = context.saved_release_calendar_page_details["title"]
    context.original_status = context.saved_release_calendar_page_details["status"]

    if status == "Cancelled":
        context.page.locator("#panel-child-content-metadata-content div").filter(
            has_text="Cancellation notice Used for"
        ).get_by_role("textbox").fill("Cancelled notice")

    # enter new details
    context.page.get_by_placeholder("Page title*").fill("New title")
    context.page.get_by_label("Status*").select_option((status).upper())
    formatted_date = new_date.strftime("%Y-%m-%d %H:%M")
    context.page.get_by_role("textbox", name="Release date*").fill(formatted_date)
    context.page.get_by_role("button", name="Save draft").click()
    # tracks new release date with ons date format
    context.saved_release_calendar_page_details["release_date_value"] = ons_date_format(new_date, "DATETIME_FORMAT")


@step("returns to the bundle edit page")
def returns_to_bundle_edit_page(
    context: Context,
) -> None:
    with context.page.expect_popup() as bundle_admin_view:
        context.page.locator("#panel-child-content-metadata-content").get_by_role("link", name="Bundle").click()
    # closes release calendar page edit view
    context.page.close()
    # assigns context to new bundles edit view
    context.page = bundle_admin_view.value


@then('the user sees the updated release calendar page\'s title, release date and the status "{status}"')
def user_sees_updated_release_calendar_page_title_release_date_status(context: Context, status: str) -> None:
    expect(
        context.page.get_by_text(
            f"New title ({status}, {context.saved_release_calendar_page_details['release_date_value']})"
        )
    ).to_be_visible()
    expect(
        context.page.get_by_text(f"{context.original_title} ({context.original_status}, {context.original_date})")
    ).not_to_be_visible()
