from datetime import datetime
from typing import TYPE_CHECKING, Any

import jinja2
from django import template
from django.template.loader import render_to_string
from django.utils.html import json_script as _json_script
from django_jinja import library
from wagtail.contrib.routable_page.templatetags.wagtailroutablepage_tags import routablepageurl
from wagtail.models import Page

from cms.core.custom_date_format import ons_date_format

register = template.Library()

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


@library.global_function
@jinja2.pass_context
def include_django(context: jinja2.runtime.Context, template_name: str) -> SafeString:
    """Allow importing a pre-rendered Django template into jinja2."""
    return render_to_string(template_name, context=dict(context), request=context.get("request", None))


def set_attributes_filter(attributes: dict, new_attributes: dict) -> dict:
    """Update attributes dictionary with new_attributes.
    This is a Python reimplementation of the Nunjucks setAttributes filter.
    See:
    https://github.com/ONSdigital/design-system/blob/d4d4e171690141678af022379273f1e408f5a4e3/lib/filters/set-attributes.js#L1-L9
    Usage in template: {{ attributes|setAttributes(new_attributes) }}.
    """
    attributes.update(new_attributes)
    return attributes


@register.filter(name="ons_date")
def ons_date_format_filter(value: datetime | None, format_string: str) -> str:
    """Format a date using the ons_date_format function."""
    return "" if value is None else ons_date_format(value, format_string)


# Copy django's json_script filter
@register.filter(is_safe=True)
def json_script(value: dict[str, Any], element_id: str | None = None) -> SafeString:
    """Output value JSON-encoded, wrapped in a <script type="application/json">
    tag (with an optional id).
    """
    return _json_script(value, element_id)


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


@register.filter(name="routablepageurl")
def routablepageurl_no_trailing_slash(
    context: jinja2.runtime.Context,
    page: Page,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Overwrite Wagtail's routablepageurl to remove trailing slash."""
    return routablepageurl(context, page, *args, **kwargs).rstrip("/")
