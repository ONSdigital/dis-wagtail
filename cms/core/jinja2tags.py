from typing import TYPE_CHECKING

from django.templatetags.static import static
from jinja2 import pass_context
from jinja2.ext import Extension
from wagtail.contrib.routable_page.templatetags.wagtailroutablepage_tags import routablepageurl
from wagtailmath.templatetags.wagtailmath import mathjax

from cms.core.templatetags.util_tags import set_attributes_filter, social_image, social_text

if TYPE_CHECKING:
    from jinja2 import Environment


class CoreExtension(Extension):  # pylint: disable=abstract-method
    """Extends the Jinja functionality with additional Django, Wagtail,
    and other package template tags.
    """

    def __init__(self, environment: "Environment"):
        super().__init__(environment)

        self.environment.globals.update(
            {
                "mathjax": mathjax,
                "static": static,
                "routablepageurl": pass_context(routablepageurl),
            }
        )

        self.environment.filters.update(
            {
                "social_text": social_text,
                "social_image": social_image,
                "setAttributes": set_attributes_filter,
            }
        )
