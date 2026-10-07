import importlib
import json
import os
from unittest import mock

import responses
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from wagtail.contrib.frontend_cache.utils import purge_urls_from_cache

from cms.frontend_cache.backends import CloudflareBackend
from cms.settings import base

# No real requests are made: @responses.activate intercepts all HTTP calls from `requests`.
# Each test registers a fake reply for this URL with `responses.post(PURGE_URL, ...)`, and
# any unregistered URL raises ConnectionError. The zone ID and token are fake too.
PURGE_URL = "https://api.cloudflare.com/client/v4/zones/test-zone/purge_cache"


def make_urls(count):
    return [f"https://example.com/{i}" for i in range(count)]


def sent_batches():
    return [json.loads(call.request.body)["files"] for call in responses.calls]


class CloudflareBackendTestCase(SimpleTestCase):
    def make_backend(self, **params):
        return CloudflareBackend({"BEARER_TOKEN": "token", "ZONEID": "test-zone", **params})

    def reload_settings(self, batch_size):
        # Settings are read from env at import time, so reload the settings module with the patched
        # env below... Reload it again after the test so later tests don't see the patched values.
        self.addCleanup(importlib.reload, base)

        with mock.patch.dict(
            os.environ,
            {
                "FRONTEND_CACHE_CLOUDFLARE_BEARER_TOKEN": "token",
                "FRONTEND_CACHE_CLOUDFLARE_ZONEID": "test-zone",
                "CLOUDFLARE_URL_PURGE_BATCH_SIZE": batch_size,
            },
            clear=False,
        ):
            return importlib.reload(base)

    @responses.activate
    def test_purge_uses_batch_size_from_env(self):
        responses.post(PURGE_URL, json={"success": True})
        urls = make_urls(5)
        reloaded_base = self.reload_settings("2")

        purge_urls_from_cache(urls, backend_settings=reloaded_base.WAGTAILFRONTENDCACHE)

        self.assertEqual(sent_batches(), [urls[0:2], urls[2:4], urls[4:5]])

    def test_invalid_batch_size_from_env_raises(self):
        for value in ("0", "-1", "501"):
            with (
                self.subTest(value=value),
                self.assertRaisesMessage(ImproperlyConfigured, "CLOUDFLARE_URL_PURGE_BATCH_SIZE"),
            ):
                self.reload_settings(value)

    def test_batch_size_boundaries_from_env_are_accepted(self):
        for value in ("1", "500"):
            with self.subTest(value=value):
                reloaded_base = self.reload_settings(value)
                self.assertEqual(reloaded_base.WAGTAILFRONTENDCACHE["default"]["PURGE_BATCH_SIZE"], int(value))

    @responses.activate
    def test_purge_is_split_into_batches_of_configured_size(self):
        responses.post(PURGE_URL, json={"success": True})
        urls = make_urls(5)
        backend_settings = {
            "default": {
                "BACKEND": "cms.frontend_cache.backends.CloudflareBackend",
                "BEARER_TOKEN": "token",
                "ZONEID": "test-zone",
                "PURGE_BATCH_SIZE": 3,
            }
        }

        purge_urls_from_cache(urls, backend_settings=backend_settings)

        self.assertEqual(sent_batches(), [urls[0:3], urls[3:5]])

    @responses.activate
    def test_cloudflare_errors_are_still_logged_per_url(self):
        responses.post(PURGE_URL, json={"success": False, "errors": [{"message": "Rate limited"}]})
        urls = make_urls(3)

        with self.assertLogs("wagtail.frontendcache", level="ERROR") as logs:
            self.make_backend(PURGE_BATCH_SIZE=2).purge_batch(urls)

        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(len(logs.records), 3)
        for url, message in zip(urls, logs.output, strict=True):
            self.assertIn(f"Couldn't purge '{url}' from Cloudflare. Cloudflare errors 'Rate limited'", message)
