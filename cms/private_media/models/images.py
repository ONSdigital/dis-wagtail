from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, ClassVar

from django.utils.functional import cached_property
from wagtail.images.models import AbstractImage, AbstractRendition

from cms.private_media.bulk_operations import bulk_set_file_permissions
from cms.private_media.managers import PrivateImageManager

from .mixins import PrivateMediaMixin

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile
    from wagtail.images.models import Filter
    from wagtail.models import Site


class PrivateImageMixin(PrivateMediaMixin):
    """A mixin class to be applied to a project's custom Image model,
    allowing the privacy of related files to be controlled effectively.
    """

    objects: ClassVar[PrivateImageManager] = PrivateImageManager()

    class Meta:
        abstract = True

    def get_privacy_controlled_files(self) -> Iterator[FieldFile]:
        file: FieldFile | None = getattr(self, "file", None)
        if file:
            yield file
        for rendition in self.renditions.all():  # type: ignore[attr-defined]
            rendition_file: FieldFile = rendition.file
            yield rendition_file

    def create_renditions(self, *filters: Filter) -> dict[Filter, AbstractRendition]:
        """Create image renditions and set their privacy permissions.

        Args:
            *filters: Filter objects defining the renditions to create

        Returns:
            dict: Mapping of filters to their corresponding rendition objects
        """
        created_renditions: dict[Filter, AbstractRendition] = super().create_renditions(*filters)  # type: ignore[misc]
        files = [r.file for r in created_renditions.values()]
        bulk_set_file_permissions(files, self.privacy)
        return created_renditions

    def get_privacy_controlled_serve_urls(self, sites: Iterable[Site]) -> Iterator[str]:
        """Return an iterator of fully-fledged serve URLs for this image, covering the domains for all
        provided sites.
        """
        renditions = self.renditions.all()  # type: ignore[attr-defined]
        for site in sites:
            for rendition in renditions:
                yield site.root_url + rendition.serve_url


class AbstractPrivateRendition(AbstractRendition):
    """A replacement for Wagtail's built-in `AbstractRendition` model, that should be used as
    a base for rendition models for image models subclassing `PrivateImageMixin`. This
    is necessary to ensure that only users with relevant permissions can view renditions
    for private images.
    """

    class Meta:
        abstract = True

    @staticmethod
    def construct_cache_key(image: AbstractImage, filter_cache_key: str, filter_spec: str) -> str:
        """Construct a cache key for the rendition that includes privacy status.

        Args:
            image: The source image
            filter_cache_key: The filter's cache key
            filter_spec: The filter specification string

        Returns:
            str: A unique cache key for the rendition
        """
        return "wagtail-rendition-" + "-".join(
            [
                str(image.id),
                image.file_hash,
                str(image.privacy),
                filter_cache_key,
                filter_spec,
            ]
        )

    @property
    def url(self) -> str:
        """Get the URL for accessing the rendition.

        Returns a direct file URL for public images with up-to-date permissions,
        or a permission-checking 'ServeView' URL for private or unprocessed images.

        Returns:
            str: URL for accessing the rendition
        """
        image: PrivateImageMixin = self.image  # pylint: disable=no-member
        if image.is_public and not image.has_outdated_file_permissions():
            try:
                return self.file.url  # type: ignore[no-any-return]
            except NotImplementedError:
                # file backend does not provide urls, so fall back on the serve view
                pass
        return self.serve_url

    @cached_property
    def serve_url(self) -> str:
        """Return a permission-checking 'ServeView' URL for this rendition."""
        from wagtail.images.views.serve import generate_image_url  # pylint: disable=import-outside-toplevel

        image: PrivateImageMixin = self.image  # pylint: disable=no-member
        generated_url: str = generate_image_url(image, self.filter_spec)
        return generated_url
