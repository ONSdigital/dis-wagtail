from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from wagtail.models import Page

from .pagination import CustomLimitOffsetPagination
from .serializers import ReleaseResourceSerializer, ResourceSerializer


class ResourceListView(APIView):
    """Provides the list of indexable Wagtail resources for external use.
    Only available if IS_EXTERNAL_ENV is True.
    """

    pagination_class = CustomLimitOffsetPagination

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

        # exclude certain page types (adjust the model names to match your codebase)
        exclude_model_names = [
            "HomePage",
            "ArticleSeriesPage",
            "ReleaseCalendarIndex",
            "ThemePage",
            "TopicPage",
            "Page",
        ]

        qs = [page for page in qs if page.specific_class.__name__ not in exclude_model_names]

        return qs
