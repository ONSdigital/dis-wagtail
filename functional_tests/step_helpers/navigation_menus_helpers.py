from behave.runner import Context
from playwright.sync_api import Page


def insert_block(page: Page, nth: int = 0) -> None:
    """Inserts a new column block by clicking the 'Insert a block' button."""
    page.get_by_role("button", name="Insert a block").nth(nth).click()


def fill_column_title(page: Page, col_index: int, title: str) -> None:
    """Fills the 'Column title' field for a given column index."""
    page.locator(f"#columns-{col_index}-value-title").fill(title)


def fill_column_link(page: Page, col_index: int, link_index: int, external_url: str, link_title: str = "") -> None:
    """Fills the external URL and link title for a given link index inside a column block."""
    if link_index > 0:
        page.get_by_role("button", name="Add").nth(link_index).click()

    page.locator(f"#columns-{col_index}-value-links-{link_index}-value-external_url").click()
    page.locator(f"#columns-{col_index}-value-links-{link_index}-value-external_url").fill(external_url)
    if link_title:
        page.locator(f"#columns-{col_index}-value-links-{link_index}-value-title").click()
        page.locator(f"#columns-{col_index}-value-links-{link_index}-value-title").fill(link_title)


def choose_page_link(page: Page, page_name: str = "Home") -> None:
    """Clicks on 'Choose a page' and selects the specified page from the Wagtail page chooser."""
    page.get_by_role("button", name="Choose a page").click()
    page.get_by_role("link", name=page_name).click()


def generate_columns(context: Context, num_columns: int) -> None:
    for i in range(num_columns):
        insert_block(context.page, nth=i)
        fill_column_title(context.page, col_index=i, title=f"Link Column {i + 1}")
        fill_column_link(
            context.page,
            col_index=i,
            link_index=0,
            external_url=f"https://www.link-column-{i + 1}.com/",
            link_title=f"Link Title {i + 1}",
        )
