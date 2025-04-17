from typing import TYPE_CHECKING

from rest_framework.response import Response
from rest_framework.views import APIView
from wagtail.models import Page

from cms.settings.base import SEARCH_INDEX_EXCLUDED_PAGE_TYPES

from .pagination import CustomPageNumberPagination
from .serializers import ResourceSerializer
from .utils import get_model_by_name

if TYPE_CHECKING:
    from django.http import HttpRequest


class ResourceListView(APIView):
    """Provides the list of indexable Wagtail resources for external use.
    Only available if IS_EXTERNAL_ENV is True.
    """

    pagination_class = CustomPageNumberPagination

    def get(self, request: "HttpRequest", *args: tuple, **kwargs: dict) -> Response:
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
        excluded_classes = [get_model_by_name(name) for name in SEARCH_INDEX_EXCLUDED_PAGE_TYPES]
        qs: list[Page] = Page.objects.live().public().not_exact_type(*excluded_classes).specific().defer_streamfields()

        return qs
