
# import random
from datetime import timedelta
# from typing import List

import factory
from behave import given, step, then, when # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from cms.articles.tests.factories import StatisticalArticlePageFactory, ArticleSeriesPageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory
from functional_tests.step_helpers.users import create_user


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


@step("the user goes to the bundle creation page")
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


@step("the user goes to the bundle menu page")
def go_to_bundle_menu(context: Context) -> None:
    context.page.goto(context.base_url + reverse("bundle:index"))


# bundle Menu
@step("the bundle menu shows bundle and Added by is not empty")
def bundle_menu_contains_value( context: Context) -> None:
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle.name)
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle_creator.get_full_name())


@step("the bundle menu shows bundle and Added by is empty")
def bundle_menu_does_not_contain_value(context: Context) -> None:
    expect(context.page.get_by_role("table")).to_contain_text(context.bundle.name)
    expect(context.page.get_by_role("table")).not_to_contain_text(context.bundle_creator.get_full_name())


# bundle Inspect
@step("the user can inspect Bundle details and Created by is not empty")
def the_user_can_see_the_bundle_details_with_creator(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).to_be_visible()


@step("the user can inspect Bundle details and Created by is empty")
def bundle_inspect_show(context: Context) -> None:
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text(context.bundle_creator.get_username())).not_to_be_visible()

# Bundles UI Data Setup
@given("there are {no_bundles} bundles")
def multiple_bundles_create(context: Context, no_bundles: str) -> None:
    context.bundles = []
    if no_bundles.isdigit():
        for bundle_index in range(int(no_bundles)):
            context.bundles.append(BundleFactory(approved=False, created_by=context.user_data["user"]))

@given("there are {no_preview_teams} Preview teams")
def multiple_preview_teams_create(context: Context, no_preview_teams: str) -> None:
    context.teams = []
    if no_preview_teams.isdigit():
        for preview_team_index in range(int(no_preview_teams)):
            context.teams.append(Team.objects.create(identifier="preview-team-" + str(preview_team_index),
                                                     name="Preview_Team_" +  str(preview_team_index)))

@given("there are {no_release_calendar} release calendar pages")
def multiple_release_calendar(context: Context, no_release_calendar: str) -> None:
    context.release_calendar_pages = []
    if no_release_calendar.isdigit():
        for release_calendar_index in range(int(no_release_calendar)):
            nowish = timezone.now() + timedelta(minutes=5*(release_calendar_index + 1))
            context.release_calendar_pages.append(
                ReleaseCalendarPageFactory(release_date=nowish,
                                           title="Release Calendar Page" +  str(release_calendar_index),
                                           status = ReleaseStatus.CONFIRMED
                                           ))

@given("there are {no_statistical_analysis} Statistical Analysis pages")
def multiple_statistical_analysis(context: Context, no_statistical_analysis: str) -> None:
    context.statistical_article_pages = []
    if no_statistical_analysis.isdigit():
        for statistical_analysis_index in range(int(no_statistical_analysis)):
            context.statistical_article_pages.append(StatisticalArticlePageFactory(
                parent=ArticleSeriesPageFactory(title="PSF" +  str(statistical_analysis_index)
                                                )))

@given("there is a {user_role} user")
def creat_user_by_role(context: Context, user_role: str) -> None:
    context.user_data = create_user(user_role)


@given("the {user_role} is a member of the Preview teams")
def add_user_to_preview_teams(context: Context, user_role: str) -> None:
    for team in context.teams:
        user = context.user_data['user']
        user.teams.add(team)


# Bundles UI Triggers
@when("the {user_role} logs in")
def log_in_user_by_role(context: Context, user_role: str) -> None:
    print(context.user_data["username"])
    print(context.user_data["password"])

    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.user_data["username"])
    context.page.get_by_placeholder("Enter password").fill(context.user_data["password"])
    context.page.get_by_role("button", name="Sign in").click()

@then("the user cannot create a bundle")
def the_user_cannot_add_bundles(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add bundle")).not_to_be_visible()
    expect(context.page.get_by_text("There are no bundles to")).to_be_visible()


@then("the user can create a bundle")
def add_bundle_details(context: Context ) -> None:
    search_bundle = context.bundles[random.randint(0, len(context.bundles) - 1)]
    context.page.get_by_role("link", name="Add bundle").click()
    context.page.get_by_role("textbox", name="Name*").fill(search_bundle.name)
    context.page.get_by_role("button", name="Create").click()


@step('the user can search for unknown bundle with response "{response}"' )
def search_for_new_bundle(context: Context, response: str) -> None:
    unknown_bundle = "Unkown bundle"
    if unknown_bundle not in get_bundles_names(context.bundles):
        context.page.get_by_role("textbox", name="Search term").click()
        context.page.get_by_role("textbox", name="Search term").fill(unknown_bundle)
        expect(context.page.get_by_text(response)).to_be_visible()

@step("the user can search for a known bundle")
def search_for_existing_bundle(context: Context) -> None:
    context.search_bundle = context.bundles[random.randint(0, len(context.bundles)-1)].name
    context.page.get_by_role("link", name="Bundles", exact=True).click()
    context.page.get_by_role("textbox", name="Search term").click()
    context.page.get_by_role("textbox", name="Search term").fill(context.search_bundle)
    context.page.get_by_role("textbox", name="Search term").click()
    expect(context. page.get_by_role("link", name=context.search_bundle)).to_be_visible()
    expect(context.page.get_by_text("No bundles match your query.")).not_to_be_visible()
    context.page.get_by_role("link", name=context.search_bundle).click()


@step("the user can edit the known bundle")
def can_edit_bundle(context: Context) -> None:
    search_bundle = context.bundles[random.randint(0, len(context.bundles) - 1)]
    search_release_calendar = context.release_calendar_pages[
        random.randint(0, len(context.release_calendar_pages) - 1)]
    search_preview_team = context.teams[
        random.randint(0, len(context.teams) - 1)]
    search_stats_article = context.statistical_article_pages[
        random.randint(0, len(context.statistical_article_pages) - 1)]

    # goto bundles index
    context.page.goto(context.base_url + reverse("bundle:index"))

    # search for and goto Bundle
    context.page.get_by_role("textbox", name="Search term").click()
    context.page.get_by_role("textbox", name="Search term").fill(search_bundle.name)
    expect(context.page.get_by_role("link", name=search_bundle.name)).to_be_visible()
    context.page.get_by_role("link", name=search_bundle.name).click()

    # add Release Calendar
    expect(context.page.get_by_role("button", name="Choose Release Calendar page")).to_be_visible()
    context.page.get_by_role("button", name="Choose Release Calendar page").click()
    context.page.get_by_role("textbox", name="Search term").click()
    context.page.get_by_role("textbox", name="Search term").fill(context.search_release_calendar.title())
    expect(context.page.get_by_role("link", name=context.search_release_calendar.title())).to_be_visible()
    context.page.get_by_role("row", name=context.search_release_calendar.title).get_by_role("link").click()
    context.page.get_by_role("link", name=context.search_release_calendar.title).click()

    # modify status
    context.page.locator("#id_status").select_option("IN_REVIEW")

    # add preview team
    context.page.get_by_role("button", name="Add preview team").click()
    context.page.get_by_role("textbox", name="Search term").click()
    context.page.get_by_role("textbox", name="Search term").fill(search_preview_team)
    context.page.get_by_text(search_preview_team).click()
    context.page.get_by_role("button", name="Confirm selection").click()

@step("the user cannot edit the known bundle")
def cannot_edit_bundle(context: Context) -> None:
    pass

def get_bundles_names(bundles) -> List[str]:
    return [ name.name for name in bundles ]


@step("the user can preview the known bundle")
def can_preview_bundle(context: Context) -> None:
    pass

@step("the user cannot preview the known bundle")
def can_preview_bundle(context: Context) -> None:
    pass


@step("the user cannot approve the known bundle")
def cannot_approve_bundle(context: Context) -> None:
    pass


@step("the user can approve the known bundle")
def can_approve_bundle(context: Context) -> None:
    pass
