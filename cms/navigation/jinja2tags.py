from typing import TYPE_CHECKING

from jinja2.ext import Extension

from cms.navigation.templatetags.navigation_tags import main_menu_columns, main_menu_highlights

if TYPE_CHECKING:
    from jinja2 import Environment


class NavigationExtension(Extension):  # pylint: disable=abstract-method
    """Extends the Jinja functionality with additional Django, Wagtail,
    and other package template tags.
    """

    def __init__(self, environment: "Environment"):
        super().__init__(environment)

        self.environment.globals.update(
            {"main_menu_highlights": main_menu_highlights, "main_menu_columns": main_menu_columns}
        )
