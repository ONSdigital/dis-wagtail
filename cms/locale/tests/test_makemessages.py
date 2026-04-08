import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management.base import CommandError
from django.core.management.commands.makemessages import Command as MakeMessagesCommand
from django.test import SimpleTestCase

from cms.locale.management.commands.makemessages import Command

SAMPLE_PO_CONTENT = """msgid ""
msgstr ""
"POT-Creation-Date: 2026-01-01 00:00+0000\\n"
"PO-Revision-Date: 2026-01-01 00:00+0000\\n"
"Language: cy\\n"
"MIME-Version: 1.0\\n
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

msgid "Hello"
msgstr "Helo"
"""

SAMPLE_PO_CONTENT_NEW_DATE = """msgid ""
msgstr ""
"POT-Creation-Date: 2026-01-01 12:00+0000\\n"
"PO-Revision-Date: 2026-01-01 00:00+0000\\n"
"Language: cy\\n"
"MIME-Version: 1.0\\n
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

msgid "Hello"
msgstr "Helo"
"""


SAMPLE_PO_CONTENT_NEW_ENTRY = """msgid ""
msgstr ""
"POT-Creation-Date: 2026-01-01 00:00+0000\\n"
"PO-Revision-Date: 2026-01-01 00:00+0000\\n"
"Language: cy\\n"
"MIME-Version: 1.0\\n
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

msgid "Hello"
msgstr "Helo"

msgid "Goodbye"
msgid "Hwyl fawr"
"""


class NormalizeTests(SimpleTestCase):
    """Tests for Command._normalize, which strips POT-Creation-Date headers."""

    def test_strips_pot_creation_date(self):
        content = 'msgid ""\nmsgstr ""\n"POT-Creation-Date: 2026-04-07 12:00+0000\\n"\n"Language: cy\\n"\n'
        result = Command._normalize(content) #pylint: disable=W0212
        self.assertNotIn("POT-Creation-Date", result)

    def test_preserves_other_metadata(self):
        content = (
            'msgid ""\n'
            'msgstr ""\n'
            '"POT-Creation-Date: 2026-04-07 12:00+0000\\n"\n'
            '"PO-Revision-Date: 2026-01-01 00:00+0000\\n"\n'
            '"Last-Translator: someone\\n"\n'
            '"Language: cy\\n"\n'
        )
        result = Command._normalize(content) #pylint: disable=W0212
        self.assertIn("PO-Revision-Date", result)
        self.assertIn("Last-Translator", result)
        self.assertIn("Language", result)

    def test_content_with_no_date_header_is_unchanged(self):
        content = 'msgid "Hello"\nmsgstr "Helo"\n'
        self.assertEqual(Command._normalize(content), content) # pylint: disable=W0212



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
        self.command._check_mode = True #pylint: disable=W0212
        self.command._modified_po_files = set() #pylint: disable=W0212
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

        self.assertIn(self.pofile, self.command._modified_po_files) # pylint: disable=W0212
        # we don't attempt to call msgmerge if the file didn't already exist
        mock_popen.assert_not_called()

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_unchanged_content_not_flagged(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)
        # returns stdout, stderr and status code
        mock_popen.return_value = (SAMPLE_PO_CONTENT, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # assert modified files is an empty set
        self.assertEqual(self.command._modified_po_files, set()) #pylint: disable=W0212

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_changed_content_flagged(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)

        # stdout from msgmerge is different
        mock_popen.return_value = (SAMPLE_PO_CONTENT_NEW_ENTRY, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # new file should be in modififed set
        self.assertIn(self.pofile, self.command._modified_po_files) #pylint: disable=W0212

    @patch("cms.locale.management.commands.makemessages.popen_wrapper")
    def test_if_only_diff_is_creation_date_not_flagged(self, mock_popen):
        self._create_po_file(SAMPLE_PO_CONTENT)

        # only date is different from initial content
        mock_popen.return_value = (SAMPLE_PO_CONTENT_NEW_DATE, "", 0)

        self.command.write_po_file(self.potfile, "cy")

        # assert modified files is an empty set
        self.assertEqual(self.command._modified_po_files, set()) #pylint: disable=W0212

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

        content_before = Path(self.potfile).read_text(encoding="utf-8")
        self.command.write_po_file(self.potfile, "cy")
        content_after = Path(self.potfile).read_text(encoding="utf-8")

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
        command._check_mode = False # pylint: disable=W0212

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
        command.handle(check=True, verbosity=1)

        self.assertIn("All .po files are up to date.", self.stdout.getvalue())

    @patch.object(MakeMessagesCommand, "handle")
    def test_changes_detected_exits_non_zero(self, mock_parent_handle):
        command = self._make_command()

        def simulate_changes(*args, **_):
            command._modified_po_files.add("/some/locale/cy/LC_MESSAGES/django.po") # pylint: disable=W0212

        mock_parent_handle.side_effect = simulate_changes

        with self.assertRaises(SystemExit) as ctx:
            command.handle(check=True, verbosity=1)

        self.assertEqual(ctx.exception.code, 1)

    @patch.object(MakeMessagesCommand, "handle")
    def test_changes_listed_in_stderr(self, mock_parent_handle):
        command = self._make_command()
        changed_path = "/some/locale/cy/LC_MESSAGES/django.po"

        def simulate_changes(*args, **_):
            command._modified_po_files.add("/some/locale/cy/LC_MESSAGES/django.po") # pylint: disable=W0212

        mock_parent_handle.side_effect = simulate_changes

        with self.assertRaises(SystemExit):
            command.handle(check=True, verbosity=1)

        stderr_output = self.stderr.getvalue()
        self.assertIn(changed_path, stderr_output)
        self.assertIn("The following .po files are not up to date:", stderr_output)
        self.assertIn("Run `makemessages` to update them.", stderr_output)

    @patch.object(MakeMessagesCommand, "handle")
    def test_without_check_delegates_to_default_makemessages(self, mock_parent_handle):
        command = self._make_command()
        command.handle(check=False, verbosity=1)

        mock_parent_handle.assert_called_once()

        self.assertNotIn("up to date", self.stdout.getvalue())
        self.assertEqual(self.stderr.getvalue(), "")

    @patch.object(MakeMessagesCommand, "handle")
    def test_quiet_mode_suppresses_success_message(self, _):
        command = self._make_command()
        command.handle(check=False, verbosity=0)

        self.assertEqual(self.stdout.getvalue(), "")
