import concurrent.futures
from collections.abc import Iterable

from django.conf import settings
from django.db.models.fields.files import FieldFile


def bulk_set_file_permissions(files: Iterable[FieldFile], private: bool) -> dict[FieldFile, bool]:
    results: dict[FieldFile, bool] = {}

    def set_file_permission_and_report(file: FieldFile) -> None:
        if private:
            results[file] = file.storage.make_private(file)
        else:
            results[file] = file.storage.make_public(file)

    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.PRIVATE_MEDIA_PERMISSION_SETTING_MAX_WORKERS) as executor:
        executor.map(set_file_permission_and_report, files)

    return results
