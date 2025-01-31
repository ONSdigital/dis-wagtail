from typing import TYPE_CHECKING

from jinja2.ext import Extension

from cms.navigation.templatetags.navigation_tags import breadcrumbs

if TYPE_CHECKING:
    from jinja2 import Environment


class NavigationExtension(Extension):  # pylint: disable=abstract-method
    """Extends Jinja templates with what's needed to render the navigation and breadcrumbs."""

    def __init__(self, environment: "Environment"):
        super().__init__(environment)

        self.environment.globals.update({"breadcrumbs": breadcrumbs})
