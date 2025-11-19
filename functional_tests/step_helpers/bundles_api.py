import re
from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from typing import Any

import responses
from django.conf import settings


def _prepare_bundle_contents_response(contents: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare a Bundle API contents response format.

    Args:
        contents: List of content items to include in the bundle

    Returns:
        Dictionary representing a bundle contents API response
    """
    return {
        "items": contents,
        "total_count": len(contents),
        "count": len(contents),
        "limit": 20,
        "offset": 0,
    }


def prepare_dataset_content_item(  # noqa: PLR0913  # pylint: disable=too-many-arguments
    *,
    content_id: str,
    dataset_id: str,
    edition_id: str,
    version_id: int,
    title: str = "Test Dataset",
    state: str = "APPROVED",
) -> dict[str, Any]:
    """Prepare a dataset content item for Bundle API responses.

    Args:
        content_id: The unique ID of this content item in the bundle
        dataset_id: The dataset namespace/ID
        edition_id: The edition ID
        version_id: The version ID (integer, minimum 1)
        title: The title of the dataset (optional, default: "Test Dataset").
               In the real API, this is read-only and hydrated from the dataset API.
        state: The state of the content item (default: "APPROVED", options: APPROVED, PUBLISHED)

    Returns:
        Dictionary representing a dataset content item matching Bundle API schema
    """
    return {
        "id": content_id,
        "content_type": "DATASET",
        "state": state,
        "metadata": {
            "dataset_id": dataset_id,
            "edition_id": edition_id,
            "version_id": version_id,
            "title": title,
        },
        "links": {
            "edit": f"https://example.com/edit/datasets/{dataset_id}/editions/{edition_id}/versions/{version_id}",
            "preview": f"https://example.com/preview/datasets/{dataset_id}/editions/{edition_id}/versions/{version_id}",
        },
    }


def _prepare_bundle_response(bundle_id: str, title: str, etag: str) -> dict[str, Any]:
    """Prepare a Bundle API bundle response format.

    Args:
        bundle_id: The ID of the bundle
        title: The title of the bundle
        etag: The ETag for the bundle

    Returns:
        Dictionary representing a bundle API response
    """
    return {
        "id": bundle_id,
        "title": title,
        "bundle_type": "MANUAL",
        "preview_teams": [{"id": "team-uuid-1"}],
        "state": "DRAFT",
        "created_at": "2025-07-14T10:30:00.000Z",
        "created_by": {"email": "publisher@ons.gov.uk"},
        "updated_at": "2025-07-14T10:30:00.000Z",
        "last_updated_by": {"email": "publisher@ons.gov.uk"},
        "scheduled_at": "",
        "managed_by": "WAGTAIL",
        "e_tag": etag,
        "etag_header": etag,
    }


@contextmanager
def mock_bundle_api(
    contents: list[dict[str, Any]] | None = None,
    bundle_id: str = "test-bundle-123",
    bundle_title: str = "Test Bundle",
    bundle_etag: str = "test-etag",
) -> Generator[responses.RequestsMock]:
    """Mock all Bundle API endpoints for functional tests.

    This context manager sets up mocks for all Bundle API operations:
    - POST /bundles (create bundle)
    - PUT /bundles/{bundle_id} (update bundle)
    - PUT /bundles/{bundle_id}/state (update bundle state)
    - POST /bundles/{bundle_id}/contents (add content to bundle)
    - DELETE /bundles/{bundle_id}/contents/{content_id} (delete content from bundle)
    - GET /bundles/{bundle_id}/contents (retrieve bundle contents)

    Use this in functional tests tagged with @bundle_api_enabled.

    Args:
        contents: List of content items to include in the bundle contents response
        bundle_id: The ID to use for created/updated bundles (default: "test-bundle-123")
        bundle_title: The title to use for created/updated bundles (default: "Test Bundle")
        bundle_etag: The ETag to return in responses (default: "test-etag")

    Yields:
        The mock responses object for making assertions about API calls
    """
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock_responses:
        base_url = settings.DIS_DATASETS_BUNDLE_API_BASE_URL
        escaped_base_url = re.escape(base_url)

        # Prepare response data
        bundle_response = _prepare_bundle_response(bundle_id, bundle_title, bundle_etag)
        contents_response = _prepare_bundle_contents_response(contents or [])
        # Mock POST /bundles - create bundle
        mock_responses.post(
            f"{base_url}/bundles",
            json=bundle_response,
            status=HTTPStatus.CREATED,
            headers={"ETag": bundle_etag},
        )

        # Mock GET /bundles/{bundle_id} - retrieve bundle
        mock_responses.get(
            re.compile(rf"{escaped_base_url}/bundles/[^/]+$"),
            json=bundle_response,
            status=HTTPStatus.OK,
            headers={"ETag": bundle_etag},
        )

        # Mock PUT /bundles/{bundle_id} - update bundle
        mock_responses.put(
            re.compile(rf"{escaped_base_url}/bundles/[^/]+$"),
            json=bundle_response,
            status=HTTPStatus.OK,
            headers={"ETag": bundle_etag},
        )

        # Mock PUT /bundles/{bundle_id}/state - update bundle state
        # Returns the updated bundle with the new state
        mock_responses.put(
            re.compile(rf"{escaped_base_url}/bundles/[^/]+/state$"),
            json=bundle_response,
            status=HTTPStatus.OK,
            headers={"ETag": bundle_etag},
        )

        # Mock POST /bundles/{bundle_id}/contents - add content to bundle
        # Returns the newly added content item
        mock_responses.post(
            re.compile(rf"{escaped_base_url}/bundles/[^/]+/contents$"),
            json=contents[0] if contents else {},
            status=HTTPStatus.CREATED,
        )

        # Mock DELETE /bundles/{bundle_id}/contents/{content_id} - delete content from bundle
        mock_responses.delete(
            re.compile(rf"{escaped_base_url}/bundles/[^/]+/contents/[^/]+$"),
            status=HTTPStatus.NO_CONTENT,
        )

        # Mock GET /bundles/{bundle_id}/contents - retrieve bundle contents
        mock_responses.get(
            re.compile(rf"{escaped_base_url}/bundles/[^/]+/contents(\?.*)?$"),
            json=contents_response,
            status=HTTPStatus.OK,
        )

        yield mock_responses
