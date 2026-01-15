from argparse import ArgumentParser
from typing import Any

from django.apps import apps
from django.contrib.admin.utils import NestedObjects
from django.core.exceptions import FieldDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Model, Q
from treebeard.mp_tree import MP_Node

from cms.test_data.utils import SEEDED_DATA_PREFIX

COLUMNS = {"slug", "title"}


class Command(BaseCommand):
    help = "Delete all random test data"

    def add_arguments(self, parser: ArgumentParser) -> None:
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

    def _build_collector(self) -> NestedObjects:
        collector = NestedObjects(using="default")

        for model in apps.get_models():
            lookups = self._get_lookups(model)

            if not lookups:
                continue

            self.stdout.write(f"Collecting {self.style.HTTP_INFO(model._meta.label)}")

            matching_instances = model._default_manager.filter(lookups)  # pylint: disable=protected-access

            collector.collect(matching_instances)  # type: ignore[arg-type]

            if issubclass(model, MP_Node):
                # Child nodes aren't automatically picked up by the collector.
                # They're correctly deleted, but this ensures they're displayed.
                for instance in matching_instances:
                    collector.collect(instance.get_descendants())  # type: ignore[attr-defined]

        return collector

    def handle(self, *args: Any, **options: Any) -> None:
        collector = self._build_collector()

        if not collector.data:
            self.stdout.write("No data to delete", self.style.SUCCESS)
            return

        collector.sort()

        instances_to_delete = sum(len(i) for i in collector.data.values())
        self.stdout.write(f"Found data to delete ({instances_to_delete})", self.style.NOTICE)

        if options["dry_run"]:
            for model, instances in sorted(collector.data.items(), key=lambda d: d[0]._meta.label):
                self.stdout.write(
                    f"{model._meta.label} ({self.style.ERROR(str(len(instances)))})", self.style.HTTP_INFO
                )
                for instance in sorted(instances, key=str):
                    self.stdout.write(f"\t{instance!s} ({instance.pk})")

        else:
            for model, instances in sorted(collector.data.items(), key=lambda d: d[0]._meta.label):
                self.stdout.write(
                    f"\t {self.style.HTTP_INFO(model._meta.label)}: {self.style.ERROR(str(len(instances)))}"
                )

            if options["interactive"]:
                self.stdout.write(
                    f"Enter the number of records which will be deleted ({instances_to_delete}) to continue: ",
                    ending="",
                )
                result = input()
                try:
                    int_result = int(result)
                except ValueError:
                    self.stdout.write("Invalid input", self.style.ERROR)
                    return

                if int_result != instances_to_delete:
                    self.stdout.write("Incorrect input", self.style.ERROR)
                    return

            self.stdout.write("Deleting data...", self.style.NOTICE)
            for model, instances in collector.data.items():
                # Use queryset delete methods to use any customized behaviour
                model._default_manager.filter(pk__in=[instance.pk for instance in instances]).delete()  # pylint: disable=protected-access
            self.stdout.write("Successfully deleted", self.style.SUCCESS)
