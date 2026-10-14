from typing import TYPE_CHECKING

from django.templatetags.static import static
from jinja2 import pass_context
from jinja2.ext import Extension
from wagtail.contrib.routable_page.templatetags.wagtailroutablepage_tags import routablepageurl
from wagtail.coreutils import WAGTAIL_APPEND_SLASH
from wagtail_polymath.templatetags.wagtail_polymath import polymath_scripts

from cms.core.templatetags.page_config_tags import get_page_config
from cms.core.templatetags.util_tags import (
    extend,
    json_script,
    ons_date_format_filter,
    routablepageurl_no_trailing_slash,
    set_attributes_filter,
)

if TYPE_CHECKING:
    from jinja2 import Environment


class CoreExtension(Extension):  # pylint: disable=abstract-method
    """Extends the Jinja functionality with additional Django, Wagtail,
    and other package template tags.
    """

    def __init__(self, environment: Environment):
        super().__init__(environment)

        self.environment.globals.update(
            {
                "polymath_scripts": polymath_scripts,
                "static": static,
                "routablepageurl": pass_context(
                    routablepageurl if WAGTAIL_APPEND_SLASH else routablepageurl_no_trailing_slash
                ),
                "extend": extend,
                "get_page_config": get_page_config,
            }
        )

        self.environment.filters.update(
            {
                "setAttributes": set_attributes_filter,
                "ons_date": ons_date_format_filter,
                "json_script": json_script,
            }
        )
