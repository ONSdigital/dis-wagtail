from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import F

from cms.private_media.utils import get_private_media_models


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run -- don't change anything.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = False
        if options["dry_run"]:
            self.stdout.write("This is a dry run.")
            dry_run = True

        for model in get_private_media_models():
            permissions_outdated = list(model.objects.filter(file_permissions_last_set__lt=F("privacy_last_changed")))
            self.stdout.write(f"{len(permissions_outdated)} {model.__name__} instances have outdated file permissions.")
            if permissions_outdated:
                make_private = []
                make_public = []
                for obj in permissions_outdated:
                    if obj.is_private:
                        make_private.append(obj)
                    else:
                        make_public.append(obj)

                if make_private:
                    if dry_run:
                        self.stdout.write(
                            f"Would update file permissions for {len(make_private)} private "
                            f"{model._meta.verbose_name_plural}."
                        )
                    else:
                        result = model.objects.bulk_update_file_permissions(  # type: ignore[attr-defined]
                            make_private, private=True
                        )
                        self.stdout.write(
                            f"File permissions successfully updated for {result} private "
                            f"{model._meta.verbose_name_plural}."
                        )
                if make_public:
                    if dry_run:
                        self.stdout.write(
                            f"Would update file permissions for {len(make_public)} public "
                            f"{model._meta.verbose_name_plural}."
                        )
                    else:
                        result = model.objects.bulk_update_file_permissions(  # type: ignore[attr-defined]
                            make_public, private=False
                        )
                        self.stdout.write(
                            f"File permissions successfully updated for {result} public "
                            f"{model._meta.verbose_name_plural}."
                        )
