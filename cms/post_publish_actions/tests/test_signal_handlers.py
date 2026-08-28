from unittest.mock import patch

from django.test import SimpleTestCase

from cms.post_publish_actions.signal_handlers import (
    _publishing_bundle,
    enqueue_post_publish_actions_for_bundle,
    run_post_publish_actions_handler,
)


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
        sentinel_page = object()
        sentinel_bundle = object()

        with enqueue_post_publish_actions_for_bundle(sentinel_bundle):
            run_post_publish_actions_handler(sender=None, instance=sentinel_page)

        mock_run_post_publish_actions_for.assert_called_once_with(sentinel_page, sentinel_bundle)

    @patch("cms.post_publish_actions.signal_handlers.run_post_publish_actions_for")
    def test_handler_runs_without_bundle_outside_context(self, mock_run_post_publish_actions_for):
        sentinel_page = object()

        run_post_publish_actions_handler(sender=None, instance=sentinel_page)

        mock_run_post_publish_actions_for.assert_called_once_with(sentinel_page, None)
