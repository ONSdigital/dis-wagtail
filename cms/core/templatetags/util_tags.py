from typing import TYPE_CHECKING, Optional, TypedDict

import jinja2
from django import template
from django.template.loader import render_to_string
from django_jinja import library
from wagtail.models import Locale

from cms.core.models import SocialMediaSettings

register = template.Library()

if TYPE_CHECKING:
    from django.utils.safestring import SafeString
    from wagtail.models import Page, Site

    from cms.images.models import CustomImage


class LocaleURLsDict(TypedDict):
    locale: "Locale"
    variant: "Page"
    url: str


class TranslationURLDict(TypedDict):
    url: str
    isoCode: str
    text: str
    current: bool


class HreflangDict(TypedDict):
    url: str
    lang: str


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


def _build_locale_urls(context: jinja2.runtime.Context) -> list[LocaleURLsDict]:
    """Internal helper to build a list of dicts that map each locale to:
    - its variant (or fallback to default_page if missing)
    - the final URL to use
    - the locale object itself.
    """
    page = context.get("page")
    if not page:
        return []
    default_locale = Locale.get_default()
    variants = {variant.locale_id: variant for variant in page.get_translations(inclusive=True).defer_streamfields()}
    default_page = variants.get(default_locale.pk)
    results: list[LocaleURLsDict] = []
    for locale in Locale.objects.all().order_by("pk"):
        variant = variants.get(locale.pk, default_page)
        if not variant:
            # In case a preview of a non-existent page is requested
            continue
        url = variant.get_url(request=context["request"])
        # If there's no real translation in this locale, prepend
        # the locale code to the default page's URL so that strings in
        # templates can be localized:
        if variant == default_page and locale.pk != variant.locale_id:
            url = f"/{locale.language_code}{url}"
        results.append(
            {
                "locale": locale,
                "variant": variant,
                "url": url,
            }
        )
    return results


@jinja2.pass_context
def get_translation_urls(context: jinja2.runtime.Context) -> list[TranslationURLDict]:
    """Returns a list of dictionaries containing URL, ISO code, language name,
    and whether it is the current locale.
    """
    base_urls = _build_locale_urls(context)
    urls: list[TranslationURLDict] = []
    for item in base_urls:
        locale = item["locale"]
        urls.append(
            {
                "url": item["url"],
                "isoCode": locale.language_code.split("-", 1)[0],
                "text": ("English" if locale.language_name_local == "British English" else locale.language_name_local),
                "current": locale.is_active,
            }
        )
    return urls


@jinja2.pass_context
def get_hreflangs(context: jinja2.runtime.Context) -> list[HreflangDict]:
    """Returns a list of dictionaries containing URL and the full locale code.
    Typically used for HTML 'hreflang' tags.
    """
    base_urls = _build_locale_urls(context)
    hreflangs: list[HreflangDict] = [{"url": item["url"], "lang": item["locale"].language_code} for item in base_urls]
    return hreflangs
