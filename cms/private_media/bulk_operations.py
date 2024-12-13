import concurrent.futures
import logging
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from cms.private_media.constants import Privacy

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


logger = logging.getLogger(__name__)


def bulk_set_file_permissions(files: Iterable["FieldFile"], privacy: Privacy) -> dict["FieldFile", bool]:
    """Set file permissions for an iterable of FieldFile objects, using the
    make_private() or make_public() methods of the storage backend.

    Uses a thread pool to set the file permissions in parallel where possible.

    Args:
        files: An iterable of FieldFile objects to set permissions for
        privacy: The intended privacy status for the supplied files

    Returns:
        dict[FieldFile, bool]: A mapping of files to a boolean indicating whether
        the permission setting request was successful
    """
    results: dict[FieldFile, bool] = {}

    def set_file_permission_and_report(file: "FieldFile") -> None:
        storage = file.storage
        handler: Callable[[FieldFile], bool] | None
        if privacy is Privacy.PRIVATE:
            handler = getattr(storage, "make_private", None)
        elif privacy is Privacy.PUBLIC:
            handler = getattr(storage, "make_public", None)

        if handler is None:
            raise ImproperlyConfigured(
                "%s does not implement the make_private() or make_public() methods, which is a requirement "
                "for bulk-setting file permissions.",
                storage.__class__.__name__,
            )
        else:
            results[file] = handler(file)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=int(settings.PRIVATE_MEDIA_BULK_UPDATE_MAX_WORKERS)
    ) as executor:
        executor.map(set_file_permission_and_report, files)

    return results
