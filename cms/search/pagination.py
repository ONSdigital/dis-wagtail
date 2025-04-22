from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class CustomLimitOffsetPagination(LimitOffsetPagination):
    """Limit/offset pagination that matches the DP API spec:
    - https://github.com/ONSdigital/dp-standards/blob/main/API_STANDARDS.md.
    """

    default_limit = settings.DEFAULT_LIMIT_PAGE_SIZE  # Default number of items per page
    max_limit = settings.DEFAULT_MAXIMUM_LIMIT_PAGE_SIZE  # Maximum number of items per page
    limit_query_param = "limit"  # Query parameter for the limit
    offset_query_param = "offset"  # Query parameter for the offset

    def get_paginated_response(self, data: list) -> Response:
        """Override DRF's default so we output the keys required by
        dp-standards / specification.yml.
        """
        return Response(
            {
                "count": len(data),  # number in this slice
                "items": data,  # results payload
                "limit": self.limit,  # the limit that was applied
                "offset": self.offset,  # starting index
                "total_count": self.count,  # size of the whole set
            }
        )
