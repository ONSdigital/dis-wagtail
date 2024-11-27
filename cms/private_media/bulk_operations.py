import concurrent.futures
import logging
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


logger = logging.getLogger(__name__)


def bulk_set_file_permissions(files: Iterable["FieldFile"], private: bool) -> dict["FieldFile", bool]:
    """Set file permissions for an iterable of FieldFile objects, using the
    make_private() or make_public() methods of the storage backend.

    Uses a thread pool to set the file permissions in parallel where possible.

    Args:
        files: An iterable of FieldFile objects to set permissions for
        private: If True, set the files to private, otherwise set them to public

    Returns:
        dict[FieldFile, bool]: A mapping of files to their new privacy status
    """
    results: dict[FieldFile, bool] = {}

    def set_file_permission_and_report(file: "FieldFile") -> None:
        storage = file.storage
        handler: Callable[[FieldFile], bool] | None
        handler = getattr(storage, "make_private", None) if private else getattr(storage, "make_public", None)

        if handler is None:
            logger.debug(
                "Storage backend %s does not support setting of individual file permissions, so skipping for file %s.",
                storage.__class__.__name__,
                file.name,
            )
        else:
            results[file] = handler(file)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=int(settings.PRIVATE_MEDIA_PERMISSION_SETTING_MAX_WORKERS)
    ) as executor:
        executor.map(set_file_permission_and_report, files)

    return results
