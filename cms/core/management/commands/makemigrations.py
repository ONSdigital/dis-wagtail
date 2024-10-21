"""Override of Django makemigrations.

This ensure the patches in __init__ are picked up.
"""

from django.core.management.commands.makemigrations import Command

__all__ = ["Command"]
