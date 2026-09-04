from __future__ import annotations

from typing import TYPE_CHECKING

from wagtail.documents.permissions import permission_policy as document_permission_policy

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cms.datavis.models import RenderedChartImage
    from cms.users.models import User


class RenderedChartImagePermissionPolicy:
    """A minimal permission policy for `RenderedChartImage`, for use with `user_can_access_asset`.

    Unlike documents and images, `RenderedChartImage` has no collection and no admin UI of its
    own to assign per-instance permissions against; it's populated only by the chart render
    pipeline. So instead of a per-instance check, editorial access is gated on the general
    Wagtail document permissions, since anyone who can manage documents already handles
    similarly-private media. Draft-preview access (e.g. via a bundle preview link) is handled
    separately by the bundle-preview cookie check in `user_can_access_asset`, not this policy.
    """

    def user_has_any_permission_for_instance(
        self,
        user: User,
        actions: Sequence[str],
        instance: RenderedChartImage,  # pylint: disable=unused-argument
    ) -> bool:
        return bool(document_permission_policy.user_has_any_permission(user, actions))


rendered_chart_image_permission_policy = RenderedChartImagePermissionPolicy()
