from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.staticfiles.finders import get_finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import Http404
from whitenoise.middleware import WhiteNoiseMiddleware

if TYPE_CHECKING:
    from whitenoise.responders import StaticFile


class CMSWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """Restrict access to certain static files in external environment.

    Whitenoise access files in 2 ways:

    1. During development, by using finders to find files at request time. This is intercepted in `find_file`,
       and responds with a 404 for unknown files.
    2. In production, by using finders to find files at startup. This is intercepted in the constructor
       and pre-filtered for allowed files.

    Only files which start with `static_prefix` are considered, to prevent breaking `WHITENOISE_ROOT`.

    The manifest file is hidden in the external environment to prevent fingerprinting. It is not filtered.
    """

    # NB: If the app isn't in `INSTALLED_APPS`, it doesn't need to be added here.
    ignore_patterns: tuple[str, ...] = (
        "wagtailadmin/*",
        "django_extensions/*",
        "wagtaildocs/*",
        "wagtailembeds/*",
        "wagtailimages/*",
        "wagtailsnippets/*",
        "wagtailusers/*",
        "js/blocks/*",
    )
    files: dict = {}  # noqa: RUF012

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.known_static_files = set()

        for finder in get_finders():
            for path, _storage in finder.list(self.ignore_patterns if settings.IS_EXTERNAL_ENV else None):
                self.known_static_files.add(self.static_prefix + path)

                # Also add the cache-busted URL (if there is one)
                if cachebusted_path := self.get_static_url(path):
                    self.known_static_files.add(cachebusted_path)

        if not settings.IS_EXTERNAL_ENV:
            # Allow manifest in writable environment.
            self.known_static_files.add(staticfiles_storage.manifest_name)  # type: ignore[attr-defined]

        new_files = {}

        for path, static_file in self.files.items():
            if path.startswith(self.static_prefix) and path not in self.known_static_files:
                continue
            if (static_url := self.get_static_url(path)) and static_url not in self.known_static_files:
                continue

            new_files[path] = static_file

        self.files = new_files

    def find_file(self, url: str) -> StaticFile | None:
        if url.startswith(self.static_prefix) and url not in self.known_static_files:
            # Force a 404 here, so Django doesn't try and serve the file itself
            raise Http404

        return super().find_file(url)
