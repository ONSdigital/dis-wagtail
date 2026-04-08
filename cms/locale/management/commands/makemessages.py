import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from django.core.management.base import CommandError
from django.core.management.commands.makemessages import Command as MakeMessagesCommand, normalize_eols
from django.core.management.utils import popen_wrapper

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

STATUS_OK = 0
_POT_CREATION_DATE_RE = re.compile(r'^"POT-Creation-Date: .*?\\n"\n', re.MULTILINE)


class Command(MakeMessagesCommand):
    @override
    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--check",
            action="store_true",
            help=("Returns a non-zero exit code if .po file(s) would be modified. Does not modify file system."),
        )

    @override
    def handle(self, *args: Any, **options: Any) -> None:
        self._check_mode = options.get("check", False)
        self._modified_po_files = set()
        self.verbosity = options["verbosity"]

        super().handle(*args, **options)

        if self._check_mode:
            if self._modified_po_files:
                self.stderr.write("The following .po files are not up to date:\n")
                for path in self._modified_po_files:
                    self.stderr.write(f"  {path}\n")
                self.stderr.write("\nRun `makemessages` to update them.\n")
                raise SystemExit(1)
            elif self.verbosity > 0:
                self.stdout.write("All .po files are up to date.\n")

    @override
    def write_po_file(self, potfile: str, locale: str) -> None:
        if not self._check_mode:
            return super().write_po_file(potfile, locale)

        basedir = os.path.join(os.path.dirname(potfile), locale, "LC_MESSAGES")
        pofile = os.path.join(basedir, f"{self.domain}.po")

        # if the path doesn't already exist this must be a modification
        if not os.path.exists(pofile):
            self._modified_po_files.add(pofile)
            return

        # Get all options to msgmerge except --update so no files on disk are touched
        check_options = [opt for opt in self.msgmerge_options if opt not in ("--update", "--backup=none")]
        args = ["msgmerge"] + check_options + [pofile, potfile]
        msgs, errors, status = popen_wrapper(args)
        if errors:
            if status != STATUS_OK:
                raise CommandError(f"errors happened wile running msgmerge\n{errors}")
            elif self.verbosity > 0:
                self.stdout.write(errors)

        # Apply same formatting that makemessages usually does
        msgs = normalize_eols(msgs)
        msgs = msgs.replace(f"#. #-#-#-#-#  {self.domain}.pot (PACKAGE VERSION)  #-#-#-#-#\n", "")

        existing = Path(pofile).read_text(encoding="utf-8")

        if self._normalize(existing) != self._normalize(msgs):
            self._modified_po_files.add(pofile)

    @staticmethod
    def _normalize(content) -> str:
        """Strip out POT-Creation-Date from gettext output"""
        return _POT_CREATION_DATE_RE.sub("", content)
