import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management.base import CommandError
from django.core.management.commands.makemessages import Command as MakeMessagesCommand
from django.test import SimpleTestCase

from cms.locale.management.commands.makemessages import Command, TranslationItem

from .po_fixtures import (
    SAMPLE_PO_CONTENT,
    SAMPLE_PO_CONTENT_DIFFERENT_ORDER,
    SAMPLE_PO_CONTENT_MULTILINE,
    SAMPLE_PO_CONTENT_NEW_DATE,
    SAMPLE_PO_CONTENT_NEW_ENTRY,
    SAMPLE_PO_CONTENT_WITH_MSGCTXT,
    SAMPLE_PO_CONTENT_WITH_MULTILINE,
)


class ExtractTranslationsTests(SimpleTestCase):
    """Tests for Command._extract_msgids, which pulls only clean, non-empty msgids from .po contents."""

    def test_gets_clean_ids(self):
        inputs = ((SAMPLE_PO_CONTENT, 2), (SAMPLE_PO_CONTENT_WITH_MULTILINE, 3))
        for item in inputs:
            result = Command._extract_translations(item[0])  # pylint: disable=W0212

            self.assertEqual(len(result), item[1])

    def test_multiline_strings_cleaned_and_joined(self):
        result = Command._extract_translations(SAMPLE_PO_CONTENT_MULTILINE)  # pylint: disable=W0212

        cleaned = result.pop()

        print(repr(cleaned))
        self.assertEqual(cleaned, TranslationItem("\nsecond line\nthird line\n", "", ""))

    def test_plurals_are_extracted(self):
        result = Command._extract_translations(  # pylint: disable=W0212
            """msgid "You have %d file"
msgid_plural "You have %d files"
msgstr[0] ""
msgstr[1] ""
"""
        )
        cleaned = result.pop()
        self.assertEqual(cleaned, ("You have %d file", "", "You have %d files"))


class WritePOFileCheckModeTests(SimpleTestCase):
    """Tests for write_po_file when _check_mode is True."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.potfile = os.path.join(self.tmpdir, "django.pot")
        Path(self.potfile).write_text("", encoding="utf8")

        self.pofile_dir = os.path.join(self.tmpdir, "cy", "LC_MESSAGES")
        self.pofile = os.path.join(self.pofile_dir, "django.po")

        self.command = Command()
        # enable _check_mode
        self.command._check_mode = True  # pylint: disable=W0212
        self.command._modified_po_files = {}  # pylint: disable=W0212
        self.command.domain = "django"
        self.command.msgmerge_options = ["-q", "--backup=none", "--previous", "--update"]
        self.command.verbosity = 0
        self.command.invoked_for_django = False
        self.command.stdout = StringIO()
        self.command.stderr = StringIO()

    def _create_po_file(self, content=SAMPLE_PO_CONTENT):
        os.makedirs(self.pofile_dir, exist_ok=True)
        Path(self.pofile).write_text(content, encoding="utf-8")

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_missing_po_file_detected_as_change(self, mock_popen):
        # .po file does not exist
        self.command.write_po_file(self.potfile, "cy")

        self.assertIn(self.pofile, self.command._modified_po_files)  # pylint: disable=W0212
        # we don't attempt to call msgmerge if the file didn't already exist
        mock_popen.assert_not_called()

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_unchanged_content_not_flagged(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)
        # returns stdout, stderr and status code
        mock_popen.return_value = (SAMPLE_PO_CONTENT, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # assert modified files is an empty dict
        self.assertEqual(self.command._modified_po_files, {})  # pylint: disable=W0212

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_changed_content_flagged(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)

        # stdout from msgmerge is different
        mock_popen.return_value = (SAMPLE_PO_CONTENT_NEW_ENTRY, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # new file should be in modififed dict
        self.assertIn(("Good Morning", "", ""), self.command._modified_po_files[self.pofile])  # pylint: disable=W0212

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_adding_msgctxt_is_considered_modified(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)

        # stdout from msgmerge is different
        mock_popen.return_value = (SAMPLE_PO_CONTENT_WITH_MSGCTXT, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # should be entries in modified dict
        self.assertNotEqual(len(self.command._modified_po_files[self.pofile]), 0)  # pylint: disable=W0212

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_if_only_diff_is_creation_date_not_flagged(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)

        # only date is different from initial content
        mock_popen.return_value = (SAMPLE_PO_CONTENT_NEW_DATE, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # assert modified files is an empty dict
        self.assertEqual(self.command._modified_po_files, {})  # pylint: disable=W0212

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_does_not_flag_if_only_order_is_different(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)

        # only date is different from initial content
        mock_popen.return_value = (SAMPLE_PO_CONTENT_DIFFERENT_ORDER, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # assert modified files is an empty dict
        self.assertEqual(self.command._modified_po_files, {})  # pylint: disable=W0212

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_msgmerge_called_without_update_arg(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)
        mock_popen.return_value = (SAMPLE_PO_CONTENT, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "msgmerge")
        self.assertNotIn("--update", args)
        self.assertNotIn("--backup=none", args)

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_additional_options_preserved(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)
        mock_popen.return_value = (SAMPLE_PO_CONTENT, "", 0)
        self.command.msgmerge_options = ["-q", "--backup=none", "--previous", "--update", "--no-wrap"]

        self.command.write_po_file(self.potfile, "cy")

        args = mock_popen.call_args[0][0]
        self.assertIn("-q", args)
        self.assertIn("--previous", args)
        self.assertIn("--no-wrap", args)
        self.assertNotIn("--backup=none", args)
        self.assertNotIn("--update", args)

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_existing_po_files_not_modified(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)
        mock_popen.return_value = (SAMPLE_PO_CONTENT_NEW_ENTRY, "", 0)

        content_before = Path(self.pofile).read_text(encoding="utf-8")
        self.command.write_po_file(self.potfile, "cy")
        content_after = Path(self.pofile).read_text(encoding="utf-8")

        self.assertEqual(content_before, content_after)

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_raises_command_error_if_popen_returns_non_zero_code(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)
        mock_popen.return_value = ("", "fatal error in msgmerge", 2)

        with self.assertRaises(CommandError) as ctx:
            self.command.write_po_file(self.potfile, "cy")

        self.assertIn("msgmerge", str(ctx.exception))


class WritePOFileNormalModeTests(SimpleTestCase):
    """Tests for write_po_file when _check_mode is False."""

    @patch.object(MakeMessagesCommand, "write_po_file")
    def test_delegates_to_parent(self, mock_write_parent):
        command = Command()
        command._check_mode = False  # pylint: disable=W0212

        # disable qa as using mocked version of function
        command.write_po_file("/tmp/django.pot", "cy")  # noqa: S108

        # disable qa as using mocked version of function
        mock_write_parent.assert_called_once_with("/tmp/django.pot", "cy")  # noqa: S108


class HandleCheckModeTests(SimpleTestCase):
    """Tests for handle() with --check flag.

    Mock out the parent MakeMessagesCommand.handle() to avoid full gettext extraction.
    Use the mock's side effect to populate _modified_po_files to simulate detecting changes.
    """

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

    def _make_command(self):
        """Create a Command with captured stdout/stderr."""
        command = Command()
        command.stdout = self.stdout
        command.stderr = self.stderr
        return command

    @patch.object(MakeMessagesCommand, "handle")
    def test_no_changes_exists_zero(self, _):
        command = self._make_command()
        command.handle(check=True, verbosity=1, jinja_engine=None)

        self.assertIn("All .po files are up to date.", self.stdout.getvalue())

    @patch.object(MakeMessagesCommand, "handle")
    def test_changes_detected_exits_non_zero(self, mock_parent_handle):
        command = self._make_command()

        def simulate_changes(*args, **_):
            command._modified_po_files["/some/locale/cy/LC_MESSAGES/django.po"] = set()  # pylint: disable=W0212

        mock_parent_handle.side_effect = simulate_changes

        with self.assertRaises(SystemExit) as ctx:
            command.handle(check=True, verbosity=1, jinja_engine=None)

        self.assertEqual(ctx.exception.code, 1)

    @patch.object(MakeMessagesCommand, "handle")
    def test_changes_listed_in_stderr(self, mock_parent_handle):
        command = self._make_command()
        changed_path = "/some/locale/cy/LC_MESSAGES/django.po"

        def simulate_changes(*args, **_):
            command._modified_po_files["/some/locale/cy/LC_MESSAGES/django.po"] = set()  # pylint: disable=W0212

        mock_parent_handle.side_effect = simulate_changes

        with self.assertRaises(SystemExit):
            command.handle(check=True, verbosity=1, jinja_engine=None)

        stderr_output = self.stderr.getvalue()
        self.assertIn(changed_path, stderr_output)
        self.assertIn("The following .po files are not up to date:", stderr_output)
        self.assertIn("Run `makemessages` to update them.", stderr_output)

    @patch.object(MakeMessagesCommand, "handle")
    def test_without_check_delegates_to_default_makemessages(self, mock_parent_handle):
        command = self._make_command()
        command.handle(check=False, verbosity=1, jinja_engine=None)

        mock_parent_handle.assert_called_once()

        self.assertNotIn("up to date", self.stdout.getvalue())
        self.assertEqual(self.stderr.getvalue(), "")

    @patch.object(MakeMessagesCommand, "handle")
    def test_quiet_mode_suppresses_success_message(self, _):
        command = self._make_command()
        command.handle(check=False, verbosity=0, jinja_engine=None)

        self.assertEqual(self.stdout.getvalue(), "")
