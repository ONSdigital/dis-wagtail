from collections.abc import Callable
from urllib.parse import ParseResult, urlencode, urlunparse

import botocore.session
import redis
from botocore.model import ServiceId
from botocore.signers import RequestSigner
from django.conf import settings
from django.core.cache import caches
from django.views.decorators.cache import cache_control
from wagtail.contrib.frontend_cache.utils import purge_url_from_cache
from wagtail.models import Site


def purge_cache_on_all_sites(path: str) -> None:
    """Purge the given path on all defined sites."""
    if settings.DEBUG:
        return

    for site in Site.objects.all():
        purge_url_from_cache(site.root_url.rstrip("/") + path)


def get_default_cache_control_kwargs() -> dict[str, int | bool]:
    """Get cache control parameters used by the cache control decorators
    used by default on most pages. These parameters are meant to be
    sane defaults that can be applied to a standard content page.
    """
    s_maxage = getattr(settings, "CACHE_CONTROL_S_MAXAGE", None)
    stale_while_revalidate = getattr(settings, "CACHE_CONTROL_STALE_WHILE_REVALIDATE", None)
    cache_control_kwargs = {
        "s_maxage": s_maxage,
        "stale_while_revalidate": stale_while_revalidate,
        "public": True,
    }
    return {k: v for k, v in cache_control_kwargs.items() if v is not None}


def get_default_cache_control_decorator() -> Callable:
    """Get cache control decorator that can be applied to views as a
    sane default for normal content pages.
    """
    cache_control_kwargs = get_default_cache_control_kwargs()
    return cache_control(**cache_control_kwargs)


class ElastiCacheIAMCredentialProvider(redis.CredentialProvider):
    """A custom redis credential provider to use IAM for authentication.

    https://redis.readthedocs.io/en/stable/examples/connection_examples.html#Connecting-to-a-redis-instance-with-ElastiCache-IAM-credential-provider.
    """

    # Authentication tokens are only valid for a maximum of 15 minutes.
    TOKEN_TTL = 900

    def __init__(self, user: str, cluster_name: str, region: str):
        self.user = user
        self.cluster_name = cluster_name
        self.region = region

        session = botocore.session.get_session()
        self.request_signer = RequestSigner(
            ServiceId("elasticache"),
            self.region,
            "elasticache",
            "v4",
            session.get_credentials(),
            session.get_component("event_emitter"),
        )

        self.cache_key = f"elasticache_{user}_{cluster_name}_{region}"

        self.connection_url = urlunparse(
            ParseResult(
                scheme="https",
                netloc=self.cluster_name,
                path="/",
                query=urlencode({"Action": "connect", "User": self.user}),
                params="",
                fragment="",
            )
        )

    def get_credentials(self) -> tuple[str, str]:
        """Get credentials from IAM."""
        if (signed_url := caches["memory"].get(self.cache_key)) is None:
            signed_url = self.request_signer.generate_presigned_url(
                {"method": "GET", "url": self.connection_url, "body": {}, "headers": {}, "context": {}},
                operation_name="connect",
                expires_in=self.TOKEN_TTL,
                region_name=self.region,
            )
            # RequestSigner only seems to work if the URL has a protocol, but
            # Elasticache only accepts the URL without a protocol
            # So strip it off the signed URL before returning
            signed_url = signed_url.removeprefix("https://")

            # Reduce cache TTL a few seconds to ensure the token is still valid
            # by the time it's used
            caches["memory"].set(self.cache_key, signed_url, self.TOKEN_TTL - 5)

        return self.user, signed_url
