# pylint: disable=protected-access

import time
from urllib.parse import parse_qs

from django.core.cache import caches
from django.test import SimpleTestCase
from moto import mock_aws

from cms.core.elasticache import ElastiCacheIAMCredentialProvider


@mock_aws
class ElastiCacheIAMCredentialProviderTestCase(SimpleTestCase):
    def setUp(self):
        caches["memory"].clear()

    def test_credentials(self):
        """Test generated credentials."""
        provider = ElastiCacheIAMCredentialProvider("user", "cluster", "eu-west-2")

        user, signed_url = provider.get_credentials()

        self.assertEqual(user, provider._user)
        self.assertTrue(signed_url.startswith("cluster"))

        querystring = parse_qs(signed_url.split("/", 1)[1][1:])

        self.assertEqual(querystring["X-Amz-Expires"], [str(provider.TOKEN_TTL)])
        self.assertEqual(querystring["Action"], ["connect"])
        self.assertEqual(querystring["User"], [provider._user])

    def test_cache(self):
        """Test cache is used."""
        provider = ElastiCacheIAMCredentialProvider("user", "cluster", "eu-west-2")

        self.assertFalse(caches["memory"].has_key(provider._cache_key))

        credentials = provider.get_credentials()

        self.assertEqual(caches["memory"].get(provider._cache_key), credentials)

        # The credentials should be the same, as they're read from a cache
        self.assertEqual(provider.get_credentials(), credentials)

        # Wait until the next second for the timestamp to change, so the signature is definitely different
        time.sleep(1 - time.time() % 1)

        # The credentials should still be the same
        self.assertEqual(provider.get_credentials(), credentials)

        caches["memory"].delete(provider._cache_key)

        # After deleting the cache, the signature should be different
        self.assertNotEqual(provider.get_credentials(), credentials)
