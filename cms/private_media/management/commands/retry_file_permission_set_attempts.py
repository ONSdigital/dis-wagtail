from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand
from django.db.models import F

from cms.private_media.constants import Privacy
from cms.private_media.models.images import PrivateImageMixin
from cms.private_media.utils import get_private_media_models

if TYPE_CHECKING:
    from cms.private_media.models import PrivateMediaMixin


class Command(BaseCommand):
    dry_run: bool

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run -- don't change anything.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.dry_run = options["dry_run"]
        if self.dry_run:
            self.stdout.write("This is a dry run.")

        for model in get_private_media_models():
            queryset = model.objects.filter(file_permissions_last_set__lt=F("privacy_last_changed"))
            if not self.dry_run and issubclass(model, PrivateImageMixin):
                queryset = queryset.prefetch_related("renditions")
            permissions_outdated = list(queryset)
            self.stdout.write(f"{len(permissions_outdated)} {model.__name__} instances have outdated file permissions.")
            if not permissions_outdated:
                continue

            make_private = []
            make_public = []
            for obj in permissions_outdated:
                if obj.privacy is Privacy.PRIVATE:
                    make_private.append(obj)
                elif obj.privacy is Privacy.PUBLIC:
                    make_public.append(obj)

            self.update_file_permissions(model, make_private, Privacy.PRIVATE)
            self.update_file_permissions(model, make_public, Privacy.PUBLIC)

    def update_file_permissions(
        self, model_class: type[PrivateMediaMixin], items: Collection[PrivateMediaMixin], privacy: Privacy
    ) -> None:
        """Update the file permissions for the provided items to reflect the provided privacy status."""
        plural = model_class._meta.verbose_name_plural
        if self.dry_run:
            self.stdout.write(f"Would update file permissions for {len(items)} {privacy} {plural}.")
        else:
            updated_count = 0
            for item in model_class.objects.bulk_set_file_permissions(  # type: ignore[attr-defined]
                items, privacy, save_changes=True
            ):
                if not item.has_outdated_file_permissions():
                    updated_count += 1

            self.stdout.write(f"File permissions successfully updated for {updated_count} {privacy} {plural}.")
