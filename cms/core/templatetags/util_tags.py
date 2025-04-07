import json
from typing import TYPE_CHECKING, Any, Optional

import jinja2
from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.utils.html import json_script as _json_script
from django_jinja import library
from jinja2.runtime import ChainableUndefined

from cms.core.models import SocialMediaSettings

register = template.Library()

if TYPE_CHECKING:
    from django.utils.safestring import SafeString
    from wagtail.models import Page, Site

    from cms.images.models import CustomImage


# Social text
@register.filter(name="social_text")
def social_text(page: "Page", site: "Site") -> str:
    """Returns the given page social text, or the default sharing image as defined in the social media settings."""
    social_text_str: str = getattr(page, "social_text", "")
    return social_text_str or SocialMediaSettings.for_site(site).default_sharing_text


# Social image
@register.filter(name="social_image")
def social_image(page: "Page", site: "Site") -> Optional["CustomImage"]:
    """Returns the given page social image, or the default sharing image as defined in the social media settings."""
    the_social_image: CustomImage | None = getattr(page, "social_image", None)
    return the_social_image or SocialMediaSettings.for_site(site).default_sharing_image


@library.global_function
@jinja2.pass_context
def include_django(context: jinja2.runtime.Context, template_name: str) -> "SafeString":
    """Allow importing a pre-rendered Django template into jinja2."""
    return render_to_string(template_name, context=dict(context), request=context.get("request", None))


# Copy django's json_script filter
@register.filter(is_safe=True)
def json_script(value: dict[str, Any], element_id: Optional[str] = None) -> "SafeString":
    """Output value JSON-encoded, wrapped in a <script type="application/json">
    tag (with an optional id).
    """
    return _json_script(value, element_id)


# FIXME: This is a temporary encoder, intended to handle encoding ChainableUndefined objects.
# Once the recent DS addition of `| tojson` is implemented in charts macros, this can be removed.
class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj: Any) -> Any:  # pylint: disable=arguments-renamed
        if isinstance(obj, ChainableUndefined):
            return None
        return super().default(obj)


# FIXME: This is a temporary filter, while the Design System components use the Nunjucks ` | dump` filter.
# Once the recent DS addition of `| tojson` is implemented in charts macros, this can be removed.
@register.filter(name="dump")
def dump(value: Any) -> str:
    """Dump a value to a string."""
    return json.dumps(value, indent=4, cls=CustomJSONEncoder)


def extend(value: list[Any], element: Any) -> None:
    """Append an item to a list.

    This could be achieved in Nunjucks with array.concat(item), and in Jinja2
    with array.append(item), but not with any syntax that is available in both.

    Use:
        {% set _ = extend(series, seriesItem) %}

    There is no actual return value, but the `set` tag should be used to avoid
    printing to the template.
    """
    if not isinstance(value, list):
        # This function is likely to be called from a template macro, so we
        # can't rely on annotations and tooling for type safety.
        raise TypeError("First argument must be a list.")
    return value.append(element)
