from typing import TYPE_CHECKING, Optional

import jinja2
from django import template
from django.template.loader import render_to_string
from django.utils.html import json_script as _json_script
from django_jinja import library

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
def json_script(value, element_id=None):
    """Output value JSON-encoded, wrapped in a <script type="application/json">
    tag (with an optional id).
    """
    return _json_script(value, element_id)
