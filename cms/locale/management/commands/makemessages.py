import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from django.core.management.base import CommandError
from django.core.management.commands.makemessages import Command as MakeMessagesCommand
from django.core.management.commands.makemessages import normalize_eols
from django.core.management.utils import popen_wrapper

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

STATUS_OK = 0
_POT_CREATION_DATE_RE = re.compile(r'^"POT-Creation-Date: [^"]+\\n"', re.MULTILINE)
_MSGID_RE = re.compile(r'^msgid\s+((?:"[^"\\]*(?:\\.[^"\\]*)*"\s*)+)', re.MULTILINE)
_MSGID_CONTENTS_RE = re.compile(r'"([^\\]*(?:\\.[^"\\]*)*)"')


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
        self._check_mode = options.get("check", False)  # pylint: disable=W0201
        self._modified_po_files: dict[str, set[str]] = {}  # pylint: disable=W0201
        self.verbosity = options["verbosity"]  # pylint: disable=W0201

        super().handle(*args, **options)

        if self._check_mode:
            if self._modified_po_files:
                self.stderr.write("The following .po files are not up to date:\n")
                for path in self._modified_po_files:
                    self.stderr.write(f"  {path}\n")
                    if len(self._modified_po_files[path]) > 0:
                        self.stderr.write("    The following msgids have changed\n")
                        for item in self._modified_po_files[path]:
                            self.stderr.write(f"    {item}\n")
                    else:
                        self.stderr.write("    new file\n")
                self.stderr.write("\nRun `makemessages` to update them.\n")
                raise SystemExit(1)
            if self.verbosity > 0:
                self.stdout.write("All .po files are up to date.\n")

    @override
    def write_po_file(self, potfile: str, locale: str) -> None:
        if not self._check_mode:
            super().write_po_file(potfile, locale)
            return

        basedir = os.path.join(os.path.dirname(potfile), locale, "LC_MESSAGES")
        pofile = os.path.join(basedir, f"{self.domain}.po")

        # if the path doesn't already exist this must be a modification
        if not os.path.exists(pofile):
            self._modified_po_files[pofile] = set()
            return

        # Get all options to msgmerge except --update (and --backup) so no files on disk
        # are touched and we get the updated contents as the first return value
        check_options = [opt for opt in self.msgmerge_options if opt not in ("--update", "--backup=none")]
        args = ["msgmerge", *check_options, pofile, potfile]
        msgs, errors, status = popen_wrapper(args)
        if errors:
            if status != STATUS_OK:
                raise CommandError(f"errors happened wile running msgmerge\n{errors}")
            if self.verbosity > 0:
                self.stderr.write(errors)

        # Apply same formatting that makemessages usually does
        msgs = normalize_eols(msgs)
        msgs = msgs.replace(f"#. #-#-#-#-#  {self.domain}.pot (PACKAGE VERSION)  #-#-#-#-#\n", "")

        existing = Path(pofile).read_text(encoding="utf-8")

        previous_msgids = self._extract_msgids(existing)
        new_msgids = self._extract_msgids(msgs)

        if previous_msgids != new_msgids:
            self._modified_po_files[potfile] = set(previous_msgids ^ new_msgids)

    @staticmethod
    def _normalize(content: str) -> str:
        """Strip out POT-Creation-Date from gettext output."""
        return _POT_CREATION_DATE_RE.sub("", content)

    @staticmethod
    def _extract_msgids(content: str) -> set[str]:
        id_set = set()
        matches = _MSGID_RE.findall(content)

        for match in matches:
            # joins multiline strings and removes surrounding quotes
            clean_id = "".join(_MSGID_CONTENTS_RE.findall(match))

            # Sometimes multiline msgids can start a line with "" so we need to check
            # for empties after we've joined and cleaned
            if clean_id == "":
                continue
            clean_id = clean_id.replace('\\"', '"').replace("\\n", "\n")
            id_set.add(clean_id)

        return id_set
