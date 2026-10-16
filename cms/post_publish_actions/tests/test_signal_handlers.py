from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

import time_machine
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from cms.post_publish_actions.signal_handlers import (
    _publishing_bundle,
    enqueue_post_publish_actions_for_bundle,
    run_post_publish_actions_handler,
)
from cms.standard_pages.tests.factories import InformationPageFactory


class EnqueuePostPublishActionsSignalTestCase(SimpleTestCase):
    def _current_bundle(self):
        return _publishing_bundle.get()

    def test_sets_and_clears(self):
        sentinel_bundle = object()

        self.assertIsNone(self._current_bundle())

        with enqueue_post_publish_actions_for_bundle(sentinel_bundle):
            self.assertIs(self._current_bundle(), sentinel_bundle)

        self.assertIsNone(self._current_bundle())

    def test_nested_inner_exit_restores_outer(self):
        outer_bundle = object()
        inner_bundle = object()

        with enqueue_post_publish_actions_for_bundle(outer_bundle):
            self.assertIs(self._current_bundle(), outer_bundle)

            with enqueue_post_publish_actions_for_bundle(inner_bundle):
                self.assertIs(self._current_bundle(), inner_bundle)

            self.assertIs(self._current_bundle(), outer_bundle)

        self.assertIsNone(self._current_bundle())

    @patch("cms.post_publish_actions.signal_handlers.run_post_publish_actions_for")
    def test_handler_enqueues_for_context_bundle(self, mock_run_post_publish_actions_for):
        sentinel_page = Mock(live=True)
        sentinel_bundle = object()

        with enqueue_post_publish_actions_for_bundle(sentinel_bundle):
            run_post_publish_actions_handler(sender=None, instance=sentinel_page)

        mock_run_post_publish_actions_for.assert_called_once_with(sentinel_page, sentinel_bundle)

    @patch("cms.post_publish_actions.signal_handlers.run_post_publish_actions_for")
    def test_handler_runs_without_bundle_outside_context(self, mock_run_post_publish_actions_for):
        sentinel_page = Mock(live=True)

        run_post_publish_actions_handler(sender=None, instance=sentinel_page)

        mock_run_post_publish_actions_for.assert_called_once_with(sentinel_page, None)

    @patch("cms.post_publish_actions.signal_handlers.run_post_publish_actions_for")
    def test_handler_skips_page_that_is_not_live(self, mock_run_post_publish_actions_for):
        run_post_publish_actions_handler(sender=None, instance=Mock(live=False))

        mock_run_post_publish_actions_for.assert_not_called()

    @patch("cms.post_publish_actions.signal_handlers.run_post_publish_actions_for")
    def test_handler_skips_page_that_is_not_live_in_bundle_context(self, mock_run_post_publish_actions_for):
        with enqueue_post_publish_actions_for_bundle(object()):
            run_post_publish_actions_handler(sender=None, instance=Mock(live=False))

        mock_run_post_publish_actions_for.assert_not_called()


class ScheduledPagePostPublishActionsTestCase(TestCase):
    def setUp(self):
        self.page = InformationPageFactory(live=False)
        self.tomorrow_go_live_at = timezone.now() + timedelta(days=1)

        patcher = patch("cms.post_publish_actions.signal_handlers.run_post_publish_actions_for")
        self.mock_run_post_publish_actions_for = patcher.start()
        self.addCleanup(patcher.stop)

    def test_scheduling_a_page_does_not_run_post_publish_actions_immediately(self):
        self.page.go_live_at = self.tomorrow_go_live_at
        self.page.save_revision().publish()

        self.page.refresh_from_db()
        self.assertFalse(self.page.live)
        self.mock_run_post_publish_actions_for.assert_not_called()

    def test_post_publish_actions_run_when_page_goes_live(self):
        self.page.go_live_at = self.tomorrow_go_live_at
        self.page.save_revision().publish()

        with time_machine.travel(self.tomorrow_go_live_at + timedelta(minutes=1)):
            call_command("publish_scheduled_without_bundles", stdout=StringIO())

        self.page.refresh_from_db()
        self.assertTrue(self.page.live)
        self.mock_run_post_publish_actions_for.assert_called_once_with(self.page, None)
        self.assertTrue(self.mock_run_post_publish_actions_for.call_args.args[0].live)
