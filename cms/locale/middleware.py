from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation
from django.utils.regex_helper import _lazy_re_compile
from django.utils.translation import get_supported_language_variant

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseBase

language_subdomain_prefix_re = _lazy_re_compile(r"^(\w+([@-]\w+){0,2})\.")


class SubdomainLocaleMiddleware(LocaleMiddleware):
    """This middleware enables locale selection based on subdomain or hostname,
    with fallback to Django's normal locale handling.

    It checks the request host against a mapping or extracts a language code from the subdomain,
    then activates that language for the request and sets the appropriate cookie.

    This allows URLs like `cy.example.com` or `en.example.com` to automatically serve content in the correct language,
    and supports explicit host-to-language mapping.
    """

    def __init__(self, get_response: Any) -> None:
        self.use_locale_subdomain = settings.CMS_USE_SUBDOMAIN_LOCALES
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> None:
        if self.use_locale_subdomain and (lang_code := self._get_language_from_host(request)):
            translation.activate(lang_code)
            request.LANGUAGE_CODE = translation.get_language()
            request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = lang_code

        super().process_request(request)

    def process_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        if (
            self.use_locale_subdomain
            and (lang_code := self._get_language_from_host(request))
            and request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, "") != lang_code
        ):
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )

        return super().process_response(request, response)

    def _get_language_from_language_code(self, lang_code: str) -> str | None:
        try:
            return get_supported_language_variant(lang_code)
        except LookupError:
            return None

    def _get_language_from_host(self, request: HttpRequest) -> str | None:
        if request.path.startswith(f"/{settings.WAGTAILADMIN_HOME_PATH.lstrip('/')}"):
            return None

        host = request.get_host()
        if host in settings.CMS_HOSTNAME_LOCALE_MAP:
            lang_code = settings.CMS_HOSTNAME_LOCALE_MAP[host]
            return self._get_language_from_language_code(lang_code)

        # If nothing was found in mapping, fallback to extracting the language code from the subdomain
        regex_match = language_subdomain_prefix_re.match(request.get_host())
        if not regex_match:
            return None

        return self._get_language_from_language_code(regex_match[1])
