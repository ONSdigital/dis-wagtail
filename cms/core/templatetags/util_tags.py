from typing import TYPE_CHECKING, Optional

import jinja2
from django import template
from django.template.loader import render_to_string
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


def set_attributes_filter(attributes: dict, new_attributes: dict) -> dict:
    """Update attributes dictionary with new_attributes.
    This is a Python reimplementation of the Nunjucks setAttributes filter.
    See:
    https://github.com/ONSdigital/design-system/blob/d4d4e171690141678af022379273f1e408f5a4e3/lib/filters/set-attributes.js#L1-L9
    Usage in template: {{ attributes|setAttributes(new_attributes) }}.
    """
    attributes.update(new_attributes)
    return attributes
