"""Overrides Django migrate.

This ensure the patches in __init__ are picked up.
"""

from django.core.management.commands.migrate import Command  # noqa: F401  # pylint: disable=unused-import
