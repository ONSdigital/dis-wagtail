from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from django.urls import reverse

from cms.private_media.managers import PrivateDocumentManager

from .mixins import PrivateMediaMixin

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile
    from wagtail.models import Site


class PrivateDocumentMixin(PrivateMediaMixin):
    """A mixin class to be applied to a project's custom Document model,
    allowing the privacy of related files to be controlled effectively.
    """

    id: int
    filename: str
    file: Any

    objects: ClassVar[PrivateDocumentManager] = PrivateDocumentManager()

    class Meta:
        abstract = True

    @property
    def url(self) -> str:
        if self.is_public and not self.has_outdated_file_permissions():
            try:
                return self.file.url  # type: ignore[no-any-return]
            except NotImplementedError:
                # file backend does not provide urls, so fall back on the serve view
                pass
        return self.serve_url

    @property
    def serve_url(self) -> str:
        return reverse("wagtaildocs_serve", args=[self.id, self.filename])

    def get_privacy_controlled_files(self) -> Iterator[FieldFile]:
        file: FieldFile | None = getattr(self, "file", None)
        if file:
            yield file

    def get_privacy_controlled_serve_urls(self, sites: Iterable[Site]) -> Iterator[str]:
        """Return an iterator of fully-fledged serve URLs for this document, covering the domains for all
        provided sites.
        """
        if not sites:
            return
        for site in sites:
            yield site.root_url + self.serve_url
