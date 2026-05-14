# pylint: disable=not-callable
from behave import given, step, then, when
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory


@given("there is a page that has been published")
def a_previously_published_page_exists(context: Context) -> None:
    context.index_page = IndexPageFactory()
    context.target_page = InformationPageFactory(parent=context.index_page, live=True)


@given("there is a page that has never been published")
def a_never_published_page_exists(context: Context) -> None:
    context.index_page = IndexPageFactory()
    context.target_page = InformationPageFactory(
        parent=context.index_page, live=False, first_published_at=None, last_published_at=None
    )


@given("there are multiple pages, some of which have been published")
def multiple_pages_mix_of_published_and_not(context: Context) -> None:
    context.index_page = IndexPageFactory()

    InformationPageFactory.create_batch(
        2, parent=context.index_page, live=False, first_published_at=None, last_published_at=None
    )
    InformationPageFactory.create_batch(2, parent=context.index_page, live=True)


@given("there are multiple pages that have never been published")
def multiple_pages_all_not_published(context: Context) -> None:
    context.index_page = IndexPageFactory()
    InformationPageFactory.create_batch(
        4, parent=context.index_page, live=False, first_published_at=None, last_published_at=None
    )


@when("the user goes to edit the page")
def user_goes_to_edit_the_target_page(context: Context) -> None:
    edit_url = reverse("wagtailadmin_pages:edit", args=[context.target_page.pk])
    context.page.goto(f"{context.base_url}{edit_url}")


@when("the user attempts to delete the page")
def user_attempts_to_delete_page(context: Context) -> None:
    context.page.get_by_role("button", name="Actions", exact=True).click()
    context.page.get_by_role("link", name="Delete").click()


@then("a banner is displayed indicating that the page cannot be deleted because it has been published previously")
def warning_banner_single_delete(context: Context) -> None:
    expect(context.page.get_by_text("Deletion Not Allowed")).to_be_visible()
    expect(context.page.get_by_text("published previously")).to_be_visible()
    # Redirected back to the edit screen for that page
    edit_url = reverse("wagtailadmin_pages:edit", args=[context.target_page.pk])
    expect(context.page).to_have_url(f"{context.base_url}{edit_url}")


@then("the page is deleted successfully")
def page_is_deleted_successfully(context: Context) -> None:
    context.page.get_by_role("button", name="Yes, delete it").click()
    expect(context.page.get_by_text(f"Page '{context.target_page.title}' deleted.")).to_be_visible()


@when("the user goes to the parent page's explorer view")
def user_goes_to_parent_page_explorer(context: Context) -> None:
    explore_url = reverse("wagtailadmin_explore", args=[context.index_page.pk])
    context.page.goto(f"{context.base_url}{explore_url}")


@when("the user selects all pages for bulk deletion")
def user_selects_all_pages_for_bulk_deletion(context: Context) -> None:
    context.page.locator("table").get_by_label("Select all").first.check()


@step("the user attempts to bulk delete the selected pages")
def user_attempts_to_bulk_delete_selected_pages(context: Context) -> None:
    context.page.get_by_label("Delete selected pages").click()
    context.page.get_by_role("button", name="Yes, delete").click()


@then(
    "a banner is displayed indicating that the selected pages cannot be deleted "
    "because they have been published previously"
)
def warning_banner_bulk_delete(context: Context) -> None:
    expect(context.page.get_by_text("Deletion Not Allowed")).to_be_visible()
    expect(context.page.get_by_text("published previously")).to_be_visible()


@then("the pages are deleted successfully")
def pages_deleted_successfully(context: Context) -> None:
    expect(context.page.get_by_text("pages have been deleted")).to_be_visible()
    expect(context.page.get_by_text("Deletion Not Allowed")).not_to_be_visible()
