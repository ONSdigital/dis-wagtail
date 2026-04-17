import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, override

from django.core.management.base import CommandError
from django.core.management.commands.makemessages import Command as MakeMessagesCommand
from django.core.management.commands.makemessages import normalize_eols
from django.core.management.utils import popen_wrapper

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

STATUS_OK = 0

_QUOTED_STR_RE = r'(?:"[^"\\]*(?:\\.[^"\\]*)*")'
_MULTILINE_QUOTED_RE = rf"(?:{_QUOTED_STR_RE}(?:\s+{_QUOTED_STR_RE})*)"

_TRANSLATION_GROUP_RE = re.compile(
    rf"(?:^msgctxt\s+(?P<msgctxt>{_MULTILINE_QUOTED_RE})\s+)?"
    rf"^msgid\s+(?P<msgid>{_MULTILINE_QUOTED_RE})"
    rf"(?:\s+msgid_plural\s+(?P<msgid_plural>{_MULTILINE_QUOTED_RE}))?",
    re.MULTILINE,
)
_MATCH_CONTENTS_RE = re.compile(r'"([^\\]*(?:\\.[^"\\]*)*)"')


class TranslationItem(NamedTuple):
    msgid: str
    msgctxt: str = ""
    msgid_plural: str = ""

    def __str__(self) -> str:
        return (
            (f"- msgctxt: {self.msgctxt}\n" if self.msgctxt != "" else "")
            + f"{'-' if self.msgctxt == '' else ' '} msgid: {self.msgid}"
            + (f"\n  msgid_plural: {self.msgid_plural}" if self.msgid_plural != "" else "")
        )


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
        self._modified_po_files: dict[str, set[TranslationItem]] = {}  # pylint: disable=W0201
        self.verbosity = options["verbosity"]  # pylint: disable=W0201

        super().handle(*args, **options)

        if self._check_mode:
            if self._modified_po_files:
                self.stderr.write("The following .po files are not up to date:\n")
                for path in self._modified_po_files:
                    self.stderr.write(f"{path}\n\n")
                    if len(self._modified_po_files[path]) > 0:
                        self.stderr.write("The following translation items have changed:\n\n")
                        for item in self._modified_po_files[path]:
                            self.stderr.write(f"{item}\n\n")
                    else:
                        self.stderr.write("new file\n")
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
                raise CommandError(f"errors occurred while running msgmerge\n{errors}")
            if self.verbosity > 0:
                self.stderr.write(errors)

        # Apply same formatting that makemessages usually does
        msgs = normalize_eols(msgs)
        msgs = msgs.replace(f"#. #-#-#-#-#  {self.domain}.pot (PACKAGE VERSION)  #-#-#-#-#\n", "")

        existing = Path(pofile).read_text(encoding="utf-8")

        previous_msgids = self._extract_translations(existing)
        new_msgids = self._extract_translations(msgs)

        if previous_msgids != new_msgids:
            self._modified_po_files[pofile] = set(previous_msgids ^ new_msgids)

    @staticmethod
    def _extract_translations(content: str) -> set[TranslationItem]:
        """Extracts groups of msgid, msgctxt and msgid_plural from pofile contents and returns
        a set of unique groups keyed with a tuple of those values in the order (msgid, msgctxt and msgid_plural).

        msgctxt and msgid_plural will default to an empty string if not present.

        Used by --check mode to detect changes that affect translation behaviour
        only. This intentionally ignores header metadata, comments, source
        references, ordering, wrapping, and other non-functional PO churn.
        """
        id_set = set[TranslationItem]()
        matches = _TRANSLATION_GROUP_RE.finditer(content)

        for match in matches:
            msgid = match.group("msgid")

            # joins multiline strings and removes surrounding quotes
            msgid = "".join(_MATCH_CONTENTS_RE.findall(msgid))

            # Sometimes multiline msgids can start a line with "" so we need to check
            # for empties after we've joined and cleaned
            if msgid == "":
                continue
            msgid = msgid.replace('\\"', '"').replace("\\n", "\n").replace('"\n"', "\n")

            msgctxt = match.group("msgctxt")
            if msgctxt:
                msgctxt = "".join(_MATCH_CONTENTS_RE.findall(msgctxt))
                msgctxt = msgctxt.replace('\\"', '"').replace("\\n", "\n")
            else:
                msgctxt = ""

            msgid_plural = match.group("msgid_plural")
            if msgid_plural:
                msgid_plural = "".join(_MATCH_CONTENTS_RE.findall(msgid_plural))
                msgid_plural = msgid_plural.replace('\\"', '"').replace("\\n", "\n")
            else:
                msgid_plural = ""

            id_set.add(TranslationItem(msgid, msgctxt, msgid_plural))

        return id_set
