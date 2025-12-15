from typing import Any

from django.apps import apps
from django.contrib.admin.utils import NestedObjects
from django.core.exceptions import FieldDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Model, Q

from .create_test_data import SEEDED_DATA_PREFIX

COLUMNS = {"slug", "title"}


class Command(BaseCommand):
    help = "Delete all random test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Just show the models to delete - don't delete anything",
        )

    def _get_lookups(self, model: type[Model]) -> Q:
        lookups = Q()
        for column in COLUMNS:
            try:
                model._meta.get_field(column)
            except FieldDoesNotExist:
                continue

            lookups |= Q(**{column + "__istartswith": SEEDED_DATA_PREFIX})

        return lookups

    def handle(self, *args: Any, **options: Any) -> None:
        collector = NestedObjects(using="default")

        for model in apps.get_models():
            lookups = self._get_lookups(model)

            if not lookups:
                continue

            self.stdout.write(f"Collecting {self.style.HTTP_INFO(model._meta.label)}")

            collector.collect(model.objects.filter(lookups))

        if not collector.data:
            self.stdout.write("No data to delete", self.style.SUCCESS)
            return

        instances_to_delete = sum(len(i) for i in collector.data.values())
        self.stdout.write(f"Found data to delete ({instances_to_delete})", self.style.NOTICE)

        if options["dry_run"]:
            for model, instances in sorted(collector.data.items(), key=lambda d: d[0]._meta.label):
                self.stdout.write(f"{model._meta.label} ({self.style.ERROR(len(instances))})", self.style.HTTP_INFO)
                for instance in sorted(instances, key=str):
                    self.stdout.write(f"\t{instance!s}")

        else:
            for model, instances in sorted(collector.data.items(), key=lambda d: d[0]._meta.label):
                self.stdout.write(f"\t {self.style.HTTP_INFO(model._meta.label)}: {self.style.ERROR(len(instances))}")

            if options["interactive"]:
                self.stdout.write(
                    f"Enter the number of records which will be deleted ({instances_to_delete}) to continue: ",
                    ending="",
                )
                result = input()
                try:
                    result = int(result)
                except ValueError:
                    self.stdout.write("Invalid input", self.style.ERROR)
                    return

                if result != instances_to_delete:
                    self.stdout.write("Incorrect input", self.style.ERROR)
                    return

            self.stdout.write("Deleting data...", self.style.NOTICE)
            deleted_count, _ = collector.delete()
            self.stdout.write(f"Successfully deleted {deleted_count} instances", self.style.SUCCESS)
