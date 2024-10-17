from django.templatetags.static import static
from jinja2 import pass_context
from jinja2.ext import Extension
from wagtail.contrib.routable_page.templatetags.wagtailroutablepage_tags import routablepageurl
from wagtailmath.templatetags.wagtailmath import mathjax

from cms.core.templatetags.util_tags import social_image, social_text


class CoreExtension(Extension):  # pylint: disable=abstract-method
    def __init__(self, environment):
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
            }
        )
