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
    def __init__(self, get_response: Any) -> None:
        self.use_locale_subdomain = getattr(settings, "CMS_USE_SUBDOMAIN_LOCALES", True)
        super().__init__(get_response)

    def process_request(self, request: "HttpRequest") -> None:
        if self.use_locale_subdomain and (lang_code := self._get_language_from_host(request)):
            translation.activate(lang_code)
            request.LANGUAGE_CODE = translation.get_language()
            request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = lang_code

        super().process_request(request)

    def process_response(self, request: "HttpRequest", response: "HttpResponseBase") -> "HttpResponseBase":
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

    def _get_language_from_host(self, request: "HttpRequest") -> str | None:
        if request.path.startswith(f"/{settings.WAGTAILADMIN_HOME_PATH.lstrip('/')}"):
            return None

        # Extract the language code from the subdomain
        regex_match = language_subdomain_prefix_re.match(request.get_host())
        if not regex_match:
            return None

        try:
            return get_supported_language_variant(regex_match[1])
        except LookupError:
            return None
