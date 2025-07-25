def insert_block(context, block_name: str, index: int = 0):
    """Inserts new empty block."""
    content_panel = context.page.locator("#panel-child-content-pre_release_access-content")

    content_panel.get_by_role("button", name="Insert a block").nth(index).click()
    context.page.get_by_role("option", name=block_name).click()


def add_basic_table(context, data=True, header=True, index=0):
    """Inserts a table block and fills with content."""
    insert_block(context, block_name="Basic table", index=index)
    if header:
        context.page.get_by_label("Table headers").select_option("column")
    context.page.get_by_role("textbox", name="Table caption").fill("Caption")

    if data:
        context.page.locator("td").first.click()
        context.page.keyboard.type("first")
        context.page.locator("td:nth-child(2)").first.click()
        context.page.keyboard.type("second")


def add_description_block(context, index=0):
    """Inserts description and fills with text."""
    insert_block(context, block_name="Description", index=index)
    context.page.get_by_role("region", name="Description *").get_by_role("textbox").fill("Description")
