import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from django_jinja.management.commands.makemessages import Command as DjangoJinjaCommand

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

    @patch.object(DjangoJinjaCommand, "write_po_file")
    def test_delegates_to_parent(self, mock_write_parent):
        command = Command()
        command._check_mode = False  # pylint: disable=W0212

        # disable qa as using mocked version of function
        command.write_po_file("/tmp/django.pot", "cy")  # noqa: S108

        # disable qa as using mocked version of function
        mock_write_parent.assert_called_once_with("/tmp/django.pot", "cy")  # noqa: S108


class CommandClassTests(SimpleTestCase):
    def test_class_is_instance_of_django_jinja_command(self):
        self.assertTrue(issubclass(Command, DjangoJinjaCommand))

    @patch("cms.locale.management.commands.makemessages.Command.handle", return_value=None)
    def test_custom_command_used(self, mock_command):
        call_command("makemessages", locale=["cy"], check=True)

        mock_command.assert_called_once()


class HandleCheckModeTests(SimpleTestCase):
    """Tests for handle() with --check flag.

    Mock out the parent DjangoJinjaCommand.handle() to avoid full gettext extraction.
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

    @patch.object(DjangoJinjaCommand, "handle")
    def test_no_changes_exists_zero(self, _):
        command = self._make_command()
        command.handle(check=True, verbosity=1, jinja_engine=None)

        self.assertIn("All .po files are up to date.", self.stdout.getvalue())

    @patch.object(DjangoJinjaCommand, "handle")
    def test_changes_detected_exits_non_zero(self, mock_parent_handle):
        command = self._make_command()

        def simulate_changes(*args, **_):
            command._modified_po_files["/some/locale/cy/LC_MESSAGES/django.po"] = set()  # pylint: disable=W0212

        mock_parent_handle.side_effect = simulate_changes

        with self.assertRaises(SystemExit) as ctx:
            command.handle(check=True, verbosity=1, jinja_engine=None)

        self.assertEqual(ctx.exception.code, 1)

    @patch.object(DjangoJinjaCommand, "handle")
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

    @patch.object(DjangoJinjaCommand, "handle")
    def test_without_check_delegates_to_default_makemessages(self, mock_parent_handle):
        command = self._make_command()
        command.handle(check=False, verbosity=1, jinja_engine=None)

        mock_parent_handle.assert_called_once()

        self.assertNotIn("up to date", self.stdout.getvalue())
        self.assertEqual(self.stderr.getvalue(), "")

    @patch.object(DjangoJinjaCommand, "handle")
    def test_quiet_mode_suppresses_success_message(self, _):
        command = self._make_command()
        command.handle(check=False, verbosity=0, jinja_engine=None)

        self.assertEqual(self.stdout.getvalue(), "")


class MakemessagesIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.tmp_dir = self.tmp_dir_obj.name
        self.addCleanup(self.tmp_dir_obj.cleanup)

        tmp_path = Path(self.tmp_dir)

        self.template_dir = tmp_path / "jinja2"
        self.template_dir.mkdir()

        self.locale_dir = tmp_path / "locale"
        self.locale_dir.mkdir()

        self.old_cwd = os.getcwd()
        os.chdir(self.tmp_dir)

        self.addCleanup(lambda cwd=self.old_cwd: os.chdir(cwd))

    def test_extract_trans_block_from_jinja2_template(self):
        template_file = self.template_dir / "text_extract.html"

        template_file.write_text(
            """
        <h1>{{ _("Cookies") }}</h1>
        {% trans trimmed name="World", place="Universe %}
            Hello {{ name }}, welcome to {{ place }}
        {% endtrans %}
        {% trans "Goodbye" %}
        """,
            encoding="utf-8",
        )

        test_templates = [
            {
                "BACKEND": "django_jinja.jinja2.Jinja2",
                "DIRS": [
                    str(self.template_dir),
                ],
                "APP_DIRS": False,
                "OPTIONS": {
                    "match_extension": ".html",
                },
            }
        ]

        with override_settings(
            TEMPLATES=test_templates,
            LOCALE_PATHS=[str(self.locale_dir)],
        ):
            call_command("makemessages", locale=["cy"], verbosity=0, domain="django")

        po_file = self.locale_dir / "cy" / "LC_MESSAGES" / "django.po"
        self.assertTrue(po_file.exists(), f"Expected .po file to exist at {po_file}")

        po_content = po_file.read_text(encoding="utf-8")

        expected_msgid_gettext = 'msgid "Cookies"'
        self.assertIn(expected_msgid_gettext, po_content)

        expected_msgid_trans_block = 'msgid "Hello %(name)s, welcome to %(place)s"'
        self.assertIn(expected_msgid_trans_block, po_content)

        expected_msgid_inline_trans = 'msgid "Goodbye"'
        self.assertIn(expected_msgid_inline_trans, po_content)
