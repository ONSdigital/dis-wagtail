import threading
import time
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase


class LockedMigrateCommandIntegrationTest(TestCase):
    def setUp(self):
        patcher = patch("cms.core.management.commands.locked_migrate.call_command", autospec=True)
        self.mock_call_command = patcher.start()
        self.addCleanup(patcher.stop)

    def assert_lock_acquired(self, stdout_buffer):
        output = stdout_buffer.getvalue().strip()
        self.assertIn("Acquiring lock", output)
        self.assertIn("Lock acquired - running migrations", output)

    def call_locked(self, *, timeout, stdout_buffer, skip_unapplied_check=True):
        args = ["--timeout", str(timeout)]
        if skip_unapplied_check:
            args.append("--skip-unapplied-check")

        call_command("locked_migrate", *args, stdout=stdout_buffer)

    def _setup_lock_side_effect(self):
        """Configure the mock to signal when the lock is held and simulate migration time."""
        lock_held = threading.Event()

        def side_effect(*args, **kwargs):
            lock_held.set()
            time.sleep(1.5)

        self.mock_call_command.side_effect = side_effect
        return lock_held

    def test_skip_unapplied_check_acquires_lock_and_runs_migrations(self):
        """When skipping unapplied check, it should always acquire the lock and run migrations."""
        stdout_buffer = StringIO()
        self.call_locked(timeout=1, stdout_buffer=stdout_buffer, skip_unapplied_check=True)
        self.assert_lock_acquired(stdout_buffer)

    @patch("cms.core.management.commands.locked_migrate.Command._has_unapplied_migrations")
    def test_has_unapplied_migration(self, mock_has_unapplied):
        """When there are unapplied migrations, it should acquire the lock and run migrations."""
        for has_pending in (True, False):
            with self.subTest(has_pending=has_pending):
                mock_has_unapplied.return_value = has_pending
                self.mock_call_command.reset_mock()
                stdout_buffer = StringIO()

                self.call_locked(timeout=1, stdout_buffer=stdout_buffer, skip_unapplied_check=False)
                if has_pending:
                    self.assert_lock_acquired(stdout_buffer=stdout_buffer)
                else:
                    self.mock_call_command.assert_not_called()

    def test_lock_timeout_under_concurrency(self):
        """Second thread should exit(1) if it can't get the lock in time."""
        first_output = StringIO()
        second_output = StringIO()
        lock_held = self._setup_lock_side_effect()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(self.call_locked, timeout=5, stdout_buffer=first_output)
            # Wait until the first thread has acquired the lock
            lock_held.wait(timeout=1)
            # Submit the second task with a shorter timeout than first thread's hold time
            second_future = executor.submit(self.call_locked, timeout=1, stdout_buffer=second_output)

            # Expect the second thread to raise SystemExit due to timeout
            with self.assertRaises(SystemExit):
                second_future.result()

            # Ensure the first thread still completes successfully
            first_future.result()

        # Only the first thread should have performed the migration
        self.assert_lock_acquired(first_output)
        # The second thread should have timed out and not run migrations
        self.assertIn("Lock took too long to acquire - aborting", second_output.getvalue().strip())
        self.assertEqual(self.mock_call_command.call_count, 1)

    def test_concurrent_calls_wait_and_runs_after_release(self):
        """If thread 2 has a longer timeout (5 seconds) than thread 1's hold time (1.5 seconds),
        it should wait until thread 1 finishes, then acquire the lock
        and run migrations successfully.
        """
        first_output = StringIO()
        second_output = StringIO()
        lock_held = self._setup_lock_side_effect()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(self.call_locked, timeout=5, stdout_buffer=first_output)
            # Wait until the first thread has acquired the lock
            lock_held.wait(timeout=1)
            second_future = executor.submit(self.call_locked, timeout=5, stdout_buffer=second_output)

            # Wait for both threads to complete
            first_future.result()
            second_future.result()

        # Both should have acquired the lock and run migrations
        self.assert_lock_acquired(first_output)
        self.assert_lock_acquired(second_output)
        self.assertEqual(self.mock_call_command.call_count, 2)
