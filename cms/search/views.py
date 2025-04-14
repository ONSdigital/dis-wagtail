from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from wagtail.models import Page

from cms.settings.base import SEARCH_INDEX_EXCLUDED_PAGE_TYPES

from .pagination import CustomPageNumberPagination
from .serializers import ReleaseResourceSerializer, ResourceSerializer


class ResourceListView(APIView):
    """Provides the list of indexable Wagtail resources for external use.
    Only available if IS_EXTERNAL_ENV is True.
    """

    pagination_class = CustomPageNumberPagination

    def get(self, request, *args, **kwargs):
        if not settings.IS_EXTERNAL_ENV:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        queryset = self.get_queryset()

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)

        # Distinguish between "release" content types vs. other
        data = []
        for page in paginated_qs:
            # breakpoint()
            if getattr(page, "search_index_content_type", None) == "release":
                serializer = ReleaseResourceSerializer(page)
            else:
                serializer = ResourceSerializer(page)
            data.append(serializer.data)

        return paginator.get_paginated_response(data)

    def get_queryset(self):
        """Returns a queryset of 'published' pages that are indexable,
        excluding pages we do not want to index.
        """
        # all published pages
        qs = Page.objects.live().specific()

        # exclude pages we do not want to index
        qs = [page for page in qs if page.specific_class.__name__ not in SEARCH_INDEX_EXCLUDED_PAGE_TYPES]

        return qs
