from behave import then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.conf import settings
from playwright.sync_api import expect

from functional_tests.step_helpers.datasets import mock_datasets_responses


@when("the user navigates to the release calendar page")
def navigate_to_release_page(context: Context):
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


@when('clicks "add child page" to create a new draft release page')
def click_add_child_page(context: Context):
    context.page.get_by_label("Add child page").click()


@when('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str):
    context.page.get_by_label("Status*").select_option(page_status.upper())


@when("enters some example content on the page")
def enter_example_release_content(context: Context):
    context.page.get_by_placeholder("Page title*").fill("My Release")

    context.page.get_by_label("Release date", exact=True).fill("2024-12-25")
    context.page.get_by_label("Release date", exact=True).press("Enter")

    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    context.page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("region", name="Release content").get_by_label("Title*").fill("My Example Content Link")

    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_label("Explore").click()
    context.page.get_by_role("link", name="Release calendar").click()

    context.page.get_by_role("button", name="Choose contact details").click()
    context.page.get_by_role("link", name=context.contact_details_snippet.name).click()

    context.page.get_by_label("Accredited Official Statistics").check()


@when("looks up and selects a dataset")
def look_up_and_select_dataset(context: Context):
    mock_dataset = {
        "id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "version": "1",
        "links": {
            "latest_version": {
                "href": "/datasets/example1/editions/example-dataset-1/versions/1",
                "id": "example1",
            },
        },
    }
    dataset_displayed_fields = {
        "title": mock_dataset["title"],
        "description": mock_dataset["description"],
        "url": settings.ONS_WEBSITE_DATASET_BASE_URL + mock_dataset["links"]["latest_version"]["href"],
    }

    context.selected_datasets = [*getattr(context, "selected_datasets", []), dataset_displayed_fields]

    with mock_datasets_responses(datasets=[mock_dataset]):
        context.page.locator("#panel-child-content-datasets-content").get_by_role(
            "button", name="Insert a block"
        ).first.click()
        context.page.get_by_text("Lookup Dataset").click()
        context.page.get_by_role("button", name="Choose a dataset").click()
        context.page.get_by_role("link", name=mock_dataset["title"]).click()
        context.page.wait_for_timeout(500)


@when("manually enters a dataset link")
def manually_enter_dataset_link(context: Context):
    context.page.locator("#panel-child-content-datasets-content").get_by_role(
        "button", name="Insert a block"
    ).first.click()
    manual_dataset = {
        "title": "Manual Dataset",
        "description": "Manually entered test dataset",
        "url": "https://example.com",
    }
    context.selected_datasets = [*getattr(context, "selected_datasets", []), manual_dataset]
    context.page.get_by_role("option", name="Manually Linked Dataset").click()
    context.page.get_by_role("region", name="Datasets").get_by_label("Title*").fill(manual_dataset["title"])
    context.page.get_by_role("region", name="Datasets").get_by_label("Description").fill(manual_dataset["description"])
    context.page.get_by_role("region", name="Datasets").get_by_label("Url*").fill(manual_dataset["url"])


@then("the new published release page with the example content is displayed")
def check_provisional_release_page_content(context: Context):
    expect(context.page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(context.page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(
        context.page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")
    ).to_be_visible()
    expect(context.page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(context.page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(context.page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()
    expect(context.page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then("the selected datasets are displayed on the page")
def check_selected_datasets_are_displayed(context: Context):
    expect(context.page.get_by_role("heading", name="Data", exact=True)).to_be_visible()

    for dataset in context.selected_datasets:
        expect(context.page.get_by_role("link", name=dataset["title"])).to_be_visible()
        expect(context.page.get_by_text(dataset["description"])).to_be_visible()
