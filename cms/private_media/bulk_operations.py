import concurrent.futures
import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from cms.private_media.constants import Privacy

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


logger = logging.getLogger(__name__)


def bulk_set_file_permissions(files: Iterable[FieldFile], privacy: Privacy) -> dict[FieldFile, bool]:
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

    # Convert generator values to a tuple to allow for repeat access
    files = tuple(files)

    for file in files:
        if privacy is Privacy.PUBLIC and not hasattr(file.storage, "make_public"):
            raise ImproperlyConfigured(
                f"{file.storage.__class__.__name__} does not implement make_public(), "
                "which is a requirement for bulk-setting of file permissions."
            )
        if privacy is Privacy.PRIVATE and not hasattr(file.storage, "make_private"):
            raise ImproperlyConfigured(
                f"{file.storage.__class__.__name__} does not implement make_private(), "
                "which is a requirement for bulk-setting of file permissions."
            )

    def set_file_permission_and_report(file: FieldFile) -> None:
        if privacy == Privacy.PRIVATE:
            results[file] = file.storage.make_private(file)  # type: ignore[attr-defined]
        elif privacy == Privacy.PUBLIC:
            results[file] = file.storage.make_public(file)  # type: ignore[attr-defined]

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=int(settings.PRIVATE_MEDIA_BULK_UPDATE_MAX_WORKERS)
    ) as executor:
        executor.map(set_file_permission_and_report, files)

    return results
