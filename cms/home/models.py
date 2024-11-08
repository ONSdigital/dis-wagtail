from typing import ClassVar

from wagtail.admin.panels import FieldPanel, Panel

from cms.core.blocks import PanelBlock
from cms.core.fields import StreamField
from cms.core.models import BasePage


class HomePage(BasePage):  # type: ignore[django-manager-missing]
    """The homepage model. Currently, only a placeholder."""

    template = "templates/pages/home_page.html"

    # Only allow creating HomePages at the root level
    parent_page_types: ClassVar[list[str]] = ["wagtailcore.Page"]


class ExamplePage(BasePage):
    """Example purely added for the sake of test investigation."""

    template = "templates/pages/example_page.html"
    parent_page_types: ClassVar[list[str]] = ["home.HomePage", "home.ExamplePage"]

    body = StreamField(
        [
            ("panel", PanelBlock()),
        ],
        blank=False,
        null=False,
    )

    content_panels: ClassVar[list[Panel]] = [
        *BasePage.content_panels,
        FieldPanel("body"),
    ]
