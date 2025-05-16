from typing import TYPE_CHECKING

from jinja2.ext import Extension

from cms.navigation.templatetags.navigation_tags import (
    breadcrumbs,
    footer_menu_columns,
    main_menu_columns,
    main_menu_highlights,
)

if TYPE_CHECKING:
    from jinja2 import Environment


class NavigationExtension(Extension):  # pylint: disable=abstract-method
    """Extends Jinja templates with what's needed to render the navigation."""

    def __init__(self, environment: "Environment"):
        super().__init__(environment)

        self.environment.globals.update(
            {
                "breadcrumbs": breadcrumbs,
                "footer_menu_columns": footer_menu_columns,
                "main_menu_columns": main_menu_columns,
                "main_menu_highlights": main_menu_highlights,
            }
        )
