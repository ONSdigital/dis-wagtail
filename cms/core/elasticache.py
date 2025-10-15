"""Helpers for Elasticache.

This module is imported in settings, so cannot import any models.
"""

from urllib.parse import SplitResult, urlencode, urlunsplit

import botocore.session
import redis
from botocore.model import ServiceId
from botocore.signers import RequestSigner
from cache_memoize import cache_memoize


class ElastiCacheIAMCredentialProvider(redis.CredentialProvider):
    """A custom redis credential provider to use IAM for authentication.

    https://redis.readthedocs.io/en/stable/examples/connection_examples.html#Connecting-to-a-redis-instance-with-ElastiCache-IAM-credential-provider.
    """

    # Authentication tokens are only valid for a maximum of 15 minutes.
    TOKEN_TTL = 900

    # Reduce cache TTL a few seconds to ensure the token is still valid
    # by the time it's used
    CACHE_TTL = TOKEN_TTL - 5

    def __init__(self, user: str, cluster_name: str, region: str):
        self._user = user
        self._cluster_name = cluster_name
        self._region = region

        self._session = botocore.session.get_session()
        credentials = self._session.get_credentials()
        event_emitter = self._session.get_component("event_emitter")

        self._request_signer = RequestSigner(
            ServiceId("elasticache"),
            self._region,
            "elasticache",
            "v4",
            credentials,
            event_emitter,
        )

        self._cache_key = f"elasticache_{user}_{cluster_name}_{region}"

    @cache_memoize(CACHE_TTL, key_generator_callable=lambda self: self._cache_key, cache_alias="memory")
    def get_credentials(self) -> tuple[str, str]:
        """Get credentials from IAM."""
        connection_url = urlunsplit(
            SplitResult(
                scheme="https",
                netloc=self._cluster_name,
                path="/",
                query=urlencode({"Action": "connect", "User": self._user}),
                fragment="",
            )
        )

        signed_url = self._request_signer.generate_presigned_url(
            {"method": "GET", "url": connection_url, "body": {}, "headers": {}, "context": {}},
            operation_name="connect",
            expires_in=self.TOKEN_TTL,
            region_name=self._region,
        )

        # RequestSigner only seems to work if the URL has a protocol, but
        # Elasticache only accepts the URL without a protocol
        # So strip it off the signed URL before returning
        signed_url = signed_url.removeprefix("https://")

        return self._user, signed_url
