import json
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand

from cms.test_data.config import TestDataConfig


class Command(BaseCommand):
    help = "Output test data config or schema, for reference when writing custom configs"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--schema",
            action="store_true",
            help="Output the JSON schema, rather than the default",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        default_config = TestDataConfig()

        if options["schema"]:
            self.stdout.write(json.dumps(default_config.model_json_schema(), indent=4))
        else:
            self.stdout.write(default_config.model_dump_json(indent=4))
