from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from wagtail.models import Page

from .pagination import CustomLimitOffsetPagination
from .serializers import ResourceSerializer
from .utils import get_model_by_name

if TYPE_CHECKING:
    from django.http import HttpRequest


class ResourceListView(APIView):
    """Provides the list of indexable Wagtail resources."""

    pagination_class = CustomLimitOffsetPagination

    def dispatch(self, request: HttpRequest, *args: tuple, **kwargs: dict) -> Response:
        if not settings.CMS_RESOURCES_ENDPOINT_ENABLED:
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args: tuple, **kwargs: dict) -> Response:
        queryset = self.get_queryset()

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)

        data = []
        for page in paginated_qs:
            serializer = ResourceSerializer(page)
            data.append(serializer.data)

        return paginator.get_paginated_response(data)

    def get_queryset(self) -> list[Page]:
        """Returns a queryset of 'published' pages that are indexable,
        excluding pages we do not want to index.
        """
        excluded_classes = [get_model_by_name(name) for name in settings.SEARCH_INDEX_EXCLUDED_PAGE_TYPES]

        qs: list[Page] = (
            Page.objects.live()
            .public()
            .not_exact_type(*excluded_classes)
            .filter(locale__language_code__in=settings.SEARCH_INDEX_INCLUDED_LANGUAGES)
            .specific()
            .defer_streamfields()
        )

        return qs
