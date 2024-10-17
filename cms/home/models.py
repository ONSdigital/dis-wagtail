from cms.core.models import BasePage


class HomePage(BasePage):
    template = "templates/pages/home_page.html"

    # Only allow creating HomePages at the root level
    parent_page_types = ["wagtailcore.Page"]
