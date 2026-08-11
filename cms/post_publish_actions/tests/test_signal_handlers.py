from unittest.mock import patch

from django.test import SimpleTestCase

from cms.post_publish_actions.signal_handlers import (
    _suppress_post_publish_actions_signal,
    run_post_publish_actions_handler,
    suppress_post_publish_actions_signal,
)


class SuppressPostPublishActionsSignalTestCase(SimpleTestCase):
    def _is_suppressed(self):
        return getattr(_suppress_post_publish_actions_signal, "value", None)

    def test_suppresses_and_clears(self):
        self.assertIsNone(self._is_suppressed())

        with suppress_post_publish_actions_signal():
            self.assertTrue(self._is_suppressed())

        self.assertIsNone(self._is_suppressed())

    def test_nested_inner_exit_does_not_clear_outer(self):
        with suppress_post_publish_actions_signal():
            with suppress_post_publish_actions_signal():
                self.assertTrue(self._is_suppressed())
            self.assertTrue(self._is_suppressed())
        self.assertIsNone(self._is_suppressed())

    @patch("cms.post_publish_actions.signal_handlers.run_post_publish_actions_for")
    def test_handler_is_noop_while_suppressed(self, mock_run_post_publish_actions_for):
        sentinel_page = object()

        with suppress_post_publish_actions_signal():
            run_post_publish_actions_handler(sender=None, instance=sentinel_page)

        mock_run_post_publish_actions_for.assert_not_called()
