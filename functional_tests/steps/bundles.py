from datetime import timedelta

from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from wagtail.test.utils.form_data import inline_formset, nested_form_data

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
def bundle_menu_contains_value(context: Context) -> None:
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
    user = context.users[0]['user']['user']
    if no_bundles.isdigit():
        for __ in range(int(no_bundles)):
            context.bundles.append(BundleFactory(approved=False, created_by=user))

@given("there are {no_bundles} bundles created by {creator_role} with status {status}, "
       "Preview Teams {teams}, Release Calendar {add_rel_cal}, Pages {add_stat_page}")
def multiple_bundles_create(context: Context, no_bundles: str,  creator_role: str,
                            status: str, teams: str, add_rel_cal: str, add_stat_page: str) -> None:
    context.bundles = []
    if no_bundles.isdigit():
        for __ in range(int(no_bundles)):
            if not any([d for d in context.users if d['role'] == creator_role]):
                create_user_by_role(context, creator_role)
            bundle = BundleFactory()

            bundle.created_by = [d for d in context.users if d['role'] == creator_role][0]['user']['user']

            if status == "Approved":
                bundle.status = BundleStatus.APPROVED
                bundle.approved = True
            elif status == "In_Review":
                bundle.status = BundleStatus.IN_REVIEW
            else:
                bundle.status = BundleStatus.DRAFT

            if bool(teams) and hasattr(context, "teams"):
                team_name_list = []
                for team in context.teams:
                    team_name_list.append({"team": team.name})
                bundle.team = inline_formset(team_name_list)

            pages_list = []
            if bool(add_rel_cal) and hasattr(context, "release_calendar_pages"):
                for page in context.release_calendar_pages:
                    pages_list.append({"page": page.id})

            if bool(add_stat_page) and hasattr(context, "statistical_article_pages"):
                for page in context.statistical_article_pages:
                    pages_list.append({"page": page.id})
            bundle.bundled_pages = inline_formset(pages_list)
            
            context.bundles.append(bundle)

@given("there are {no_preview_teams} Preview teams")
def multiple_preview_teams_create(context: Context, no_preview_teams: str) -> None:
    context.teams = []
    if no_preview_teams.isdigit():
        for preview_team_index in range(int(no_preview_teams)):
            context.teams.append(
                Team.objects.create(
                    identifier="preview-team-" + str(preview_team_index), name="Preview_Team_" + str(preview_team_index)
                )
            )


@given("there are {no_release_calendar} release calendar pages")
def multiple_release_calendar(context: Context, no_release_calendar: str) -> None:
    context.release_calendar_pages = []
    if no_release_calendar.isdigit():
        for release_calendar_index in range(int(no_release_calendar)):
            nowish = timezone.now() + timedelta(minutes=5 * (release_calendar_index + 1))
            context.release_calendar_pages.append(
                ReleaseCalendarPageFactory(
                    release_date=nowish,
                    title="Release Calendar Page" + str(release_calendar_index),
                    status=ReleaseStatus.CONFIRMED,
                )
            )


@given("there are {no_statistical_analysis} Statistical Analysis pages")
def multiple_statistical_analysis(context: Context, no_statistical_analysis: str) -> None:
    context.statistical_article_pages = []
    if no_statistical_analysis.isdigit():
        for statistical_analysis_index in range(int(no_statistical_analysis)):
            context.statistical_article_pages.append(
                StatisticalArticlePageFactory(
                    parent=ArticleSeriesPageFactory(title="PSF" + str(statistical_analysis_index))
                )
            )


@given("there is a {user_role} user")
def create_user_by_role(context: Context, user_role: str) -> None:
    if 'users' not in context:
        context.users = []
    if not any([d for d in context.users if d['role'] == user_role]):
        user_data = create_user(user_role)
        context.users.append({'role': user_role, 'user': user_data})

@given("the {user_role} is a member of the Preview teams")
def add_user_to_preview_teams(context: Context, user_role : str) -> None:
    if any([d for d in context.users if d['role'] == user_role]):
        user = [d for d in context.users if d['role'] == user_role][0]['user']['user']
        for team in context.teams:
            user.teams.add(team)

# Bundles UI Triggers
@when("the {user_role} logs in")
def log_in_user_by_role(context: Context, user_role: str) -> None:
    user = [d for d in context.users if d['role'] == user_role][0]['user']
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(user["username"])
    context.page.get_by_placeholder("Enter password").fill(user["password"])
    context.page.get_by_role("button", name="Sign in").click()


@then("the user cannot create a bundle")
def the_user_cannot_add_bundles(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add bundle")).not_to_be_visible()
    expect(context.page.get_by_text("There are no bundles to")).to_be_visible()


@then("the user can create a bundle")
def add_bundle_details(context: Context) -> None:
    bundle_name = "Bundle UI Test 1"
    context.page.get_by_role("link", name="Add bundle").click()
    context.page.get_by_role("textbox", name="Name*").fill(bundle_name)
    context.page.get_by_role("button", name="Create").click()


@step("the user can search for a known bundle")
def search_for_existing_bundle(context: Context) -> None:
    context.page.get_by_role("link", name="Bundles", exact=True).click()
    context.page.get_by_role("textbox", name="Search term").click()
    context.page.get_by_role("textbox", name="Search term").fill(context.bundles[0].name)
    context.page.get_by_role("textbox", name="Search term").click()
    expect(context.page.get_by_role("link", name=context.search_bundle)).to_be_visible()
    expect(context.page.get_by_text("No bundles match your query.")).not_to_be_visible()
    context.page.get_by_role("link", name=context.search_bundle).click()


@step("the user can edit a bundle")
def can_edit_bundle(context: Context) -> None:
    context.page.get_by_role("textbox", name="Search term").click()
    context.page.get_by_role("textbox", name="Search term").fill(context.bundles[0].name)
    context.page.get_by_role("link", name=context.bundles[0].name).click()

    # add Release Calendar
    if hasattr(context, "search_release_calendar"):
        expect(context.page.get_by_role("button", name="Choose Release Calendar page")).to_be_visible()
        context.page.get_by_role("button", name="Choose Release Calendar page").click()
        context.page.get_by_role("textbox", name="Search term").click()
        context.page.get_by_role("textbox", name="Search term").fill(context.search_release_calendar.title())
        expect(context.page.get_by_role("link", name=context.release_calendar_pages[0].title())).to_be_visible()
        context.page.get_by_role("row", name=context.search_release_calendar.title).get_by_role("link").click()
        context.page.get_by_role("link", name=context.search_release_calendar.title).click()

    # modify status
    context.page.locator("#id_status").select_option("IN_REVIEW")

    # add preview team
    if hasattr(context, "teams"):
        context.page.locator("#panel-preview_teams-content div").filter(has_text="Add preview team").click()
        context.page.get_by_role("button", name="Add preview team").click()
        context.page.get_by_role("textbox", name="Search term").fill(context.teams[0].name)
        context.page.get_by_role("checkbox", name=context.teams[0].name).check()
        context.page.get_by_role("button", name="Confirm selection").click()

@step("the user can preview a bundle")
def can_preview_bundle(context: Context) -> None:
    print(context.bundles[0])
    context.page1.get_by_role("link", name="Bundles UI Test 1 Bundle").click()


@step("the user cannot approve the known bundle")
def cannot_approve_bundle(context: Context) -> None:
    pass

@step("the user can approve the known bundle")
def can_approve_bundle(context: Context) -> None:
    pass
