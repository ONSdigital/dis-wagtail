# In cms/core/views.py

from typing import Any

from django.conf import settings
from django.http import Http404, HttpRequest
from django.utils.translation import activate
from wagtail.models import Locale, Site


def serve_localized_homepage(request: HttpRequest, lang_code: str) -> Any:
    """A custom view to directly serve the translated homepage for a given
    language code from a slash-less URL (e.g., /cy).

    This is necessary because using i18n_patterns would create URLs like /cy/
    which is not the desired behavior for the homepage.
    """
    if not settings.USE_I18N_ROOT_NO_TRAILING_SLASH:
        raise Http404()

    # Activate the language for this request.
    activate(lang_code)

    try:
        locale = Locale.objects.get(language_code=lang_code)
    except Locale.DoesNotExist as err:
        raise Http404("Language not supported") from err

    # Find the homepage for the current site.
    site = Site.find_for_request(request)
    if not site:
        # Fallback for environments without a hostname (e.g., management commands)
        site = Site.objects.filter(is_default_site=True).first()

    if not site or not site.root_page:
        raise Http404("Site or homepage not found")

    homepage = site.root_page.specific

    # Get the translated version of the homepage for the given language code.
    translated_homepage = homepage.get_translation_or_none(locale)

    if translated_homepage and translated_homepage.live:
        return translated_homepage.serve(request)

    # If no translation exists, fall back to the default homepage.
    return homepage.serve(request)
