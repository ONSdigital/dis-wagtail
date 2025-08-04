import json
from json import loads
from datetime import timedelta

from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundlePage, BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_to_publish
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

@given("there is a {user_role} user")
def create_user_by_role(context: Context, user_role: str) -> None:
    if 'users' not in context:
        context.users = []
    if not next(d for d in context.users if d['role'] == user_role):
        user_data = create_user(user_role)
        context.users.append({'role': user_role, 'user': user_data})


@given("there are {no_statistical_analysis} Statistical Analysis pages")
def multiple_statistical_analysis(context: Context, no_statistical_analysis: str) -> None:
    context.statistical_article_pages = []
    if no_statistical_analysis.isdigit():
        for statistical_analysis_index in range(int(no_statistical_analysis)):
            article  = StatisticalArticlePageFactory(
                parent=ArticleSeriesPageFactory(title="PSF" + str(statistical_analysis_index)))
            mark_page_as_ready_to_publish(article, UserFactory())
            context.statistical_article_pages.append(article)


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


@given("the {user_role} is a member of the Preview teams")
def add_user_to_preview_teams(context: Context, user_role : str) -> None:
    for user in [d for d in context.users if d['role'] == user_role]:
        tmp_user =user['user']['user']
        for team in context.teams:
            tmp_user.teams.add(team)


@given("there are {no_bundles} bundles with {bundle_details}")
def multiple_bundles_create(context: Context, no_bundles: str, bundle_details: str) -> None:
    bundles_details = json.loads(bundle_details)
    context.bundles = []

    if no_bundles.isdigit():
        for __ in range(int(no_bundles)):
            create_bundle(context, bundles_details["creator_role"], bundles_details["status"])

    if bool(bundles_details["preview_teams"]) and hasattr(context, "teams"):
        for team in context.teams:
            for bundle in context.bundles:
                BundleTeam.objects.create(parent=bundle, team=team)

    if bool(bundles_details["add_rel_cal"]) and hasattr(context, "release_calendar_pages"):
        for page in context.release_calendar_pages:
            for bundle in context.bundles:
                BundlePage.objects.create(parent=bundle, page=page)

    if bool(bundles_details["add_stat_page"]) and hasattr(context, "statistical_article_pages"):
        for page in context.statistical_article_pages:
            for bundle in context.bundles:
                BundlePage.objects.create(parent=bundle, page=page)


def create_bundle(context, creator_role, status):
    if not next(d for d in context.users if d['role'] == creator_role):
        create_user_by_role(context, creator_role)
    bundle_creator = next(d for d in context.users if d['role'] == creator_role)[0]['user']['user']
    bundle_status = BundleStatus.DRAFT
    bundle_approved = False
    if status == "Approved":
        bundle_status = BundleStatus.APPROVED
        bundle_approved = True
    if status == "In_Review":
        bundle_status = BundleStatus.IN_REVIEW
    bundle = BundleFactory(created_by=bundle_creator,
                           status=bundle_status,
                           approved=bundle_approved,
                           )
    context.bundles.append(bundle)


# Bundles UI Triggers
@when("the {user_role} logs in")
def log_in_user_by_role(context: Context, user_role: str) -> None:
    user = next(d for d in context.users if d['role'] == user_role)[0]['user']
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(user["username"])
    context.page.get_by_placeholder("Enter password").fill(user["password"])
    context.page.get_by_role("button", name="Sign in").click()

# Bundles UI Consequences
@then("the user can create a bundle")
def add_bundle_details(context: Context) -> None:
    bundle_name = "Bundle UI Test 1"
    context.page.get_by_role("link", name="Add bundle").click()
    context.page.get_by_role("textbox", name="Name*").fill(bundle_name)
    context.page.get_by_role("button", name="Create").click()


@then("the user cannot create a bundle")
def the_user_cannot_add_bundles(context: Context) -> None:
    expect(context.page.get_by_role("link", name="Add bundle")).not_to_be_visible()
    expect(context.page.get_by_text("There are no bundles to")).to_be_visible()


@step("the {user_role} can edit a bundle")
def can_edit_bundle(context: Context, user_role: str) -> None:
    context.page.get_by_role("textbox", name="Search term").click()
    context.page.get_by_role("textbox", name="Search term").fill(context.bundles[0].name)
    context.page.get_by_role("link", name=context.bundles[0].name).click()

    # add Release Calendar
    if hasattr(context, "search_release_calendar"):
        expect(context.page.get_by_role("button", name="Choose Release Calendar page")).to_be_visible()
        context.page.get_by_role("button", name="Choose Release Calendar page").click()
        context.page.get_by_role("textbox", name="Search term").click()
        context.page.get_by_role("textbox", name="Search term").fill(context.release_calendar_pages[0].title().title())
        expect(context.page.get_by_role("link", name=context.release_calendar_pages[0].title())).to_be_visible()
        context.page.get_by_role("row", name=context.release_calendar_pages[0].title()).get_by_role("link").click()
        context.page.get_by_role("link", name=context.release_calendar_pages[0].title()).click()

    # add Article
    if hasattr(context, "statistical_article_pages"):
       expect(context.page.get_by_role("heading", name="Bundled pages").locator("span")).to_be_visible()
       expect(context.page.get_by_role("button", name="Add page")).to_be_visible()
       expect(context.get_by_role("button", name="Add page")).click()
       context.page.get_by_role("button", name="Add page").click()
       expect(context.page.get_by_role("button", name="Choose a page")).to_be_visible()
       context.page.get_by_role("button", name="Choose a page").click()
       context.page.get_by_role("cell", name="Type").click()
       context.page.get_by_label("Page type").select_option("StatisticalArticlePage")
       expect(context.page.get_by_role("link", name=context.statistical_article_pages[0].title)).to_be_visible()
       context.page.get_by_role("link", name=context.statistical_article_pages[0].title).click()
       context.page.get_by_role("button", name="Save").click()

    # modify status
    context.page.locator("#id_status").select_option("IN_REVIEW")

    # add preview team
    if hasattr(context, "teams"):
        context.page.locator("#panel-preview_teams-content div").filter(has_text="Add preview team").click()
        context.page.get_by_role("button", name="Add preview team").click()
        context.page.get_by_role("textbox", name="Search term").fill(context.teams[0].name)
        context.page.get_by_role("checkbox", name=context.teams[0].name).check()
        context.page.get_by_role("button", name="Confirm selection").click()


@step("the {user_role} can preview a bundle")
def can_preview_bundle(context: Context, user_role: str) -> None:

    if user_role == "Viewer":
        expect(context.page.get_by_text("Bundles ready for preview")).to_be_visible()
        expect(context.page.get_by_role("link", name=context.bundles[0].name)).to_be_visible()
        context.page.get_by_role("link", name=context.bundles[0].name).click()

    else:
        expect(context.page.get_by_text("Latest active bundles")).to_be_visible()
        expect(context.page.get_by_role("link", name=context.bundles[0].name)).to_be_visible()
        expect(context.page.get_by_role("cell", name="In Preview")).to_be_visible()
        expect(context.page.get_by_role("row", name=context.bundles[0].name + " Actions")
               .get_by_label("Actions")).to_be_visible()
        (context.page.get_by_role("row", name=context.bundles[0].name + " Actions")
         .get_by_label("Actions").click())
        context.page.get_by_role("link", name="View", exact=True).click()

    expect(context.page.locator("header")).to_contain_text(context.bundles[0].name)
    expect(context.page.get_by_text("Name")).to_be_visible()
    expect(context.page.get_by_text(context.bundles[0].name).nth(2)).to_be_visible()
    expect(context.page.get_by_text("Created at")).to_be_visible()
    expect(context.page.get_by_text("Created by")).to_be_visible()
    expect(context.page.get_by_text("Associated release calendar")).to_be_visible()
    expect(context.page.get_by_text("Pages")).to_be_visible()
    expect(context.page.get_by_text("Datasets", exact=True)).to_be_visible()
    expect(context.page.get_by_text("No datasets in bundle")).to_be_visible()
    context.page.get_by_role("link", name="Preview").click()
    expect(context.page.get_by_role("heading", name="Statistical article")).to_be_visible()


@step("the {user_role} cannot preview a bundle")
def cannot_preview_bundle(context: Context, user_role: str) -> None:
        context.page.get_by_role("link", name="Bundles", exact=True).click()
        expect(context.page.get_by_role("button",
                                        name=f"More options for '{context.bundles[0].name}'")).not_to_be_visible()

@step("the {user_role} cannot approve a bundle")
def cannot_approve_bundle(context: Context, user_role: str) -> None:
    if user_role == "Viewer":
        print(user_role)
    else:
        print(user_role)


@step("the {user_role} can approve a bundle")
def can_approve_bundle(context: Context, user_role: str) -> None:
    expect(context.page.get_by_text("Latest active bundles")).to_be_visible()
    expect(context.page.get_by_role("link", name=context.bundles[0].name)).to_be_visible()
    expect(context.page.get_by_role("cell", name="In Preview")).to_be_visible()
    expect(context.page.get_by_role("row", name=context.bundles[0].name + " Actions").get_by_label(
        "Actions")).to_be_visible()
    context.page.get_by_role("row", name=context.bundles[0].name + " Actions").get_by_label("Actions").click()
    context.page.get_by_role("link", name="Edit", exact=True).click()
    context.page.locator("#id_status").select_option("APPROVED")
    context.page.get_by_role("button", name="Save").click()
