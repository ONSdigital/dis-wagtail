from rest_framework.pagination import LimitOffsetPagination


class CustomLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 20  # or from settings
    max_limit = 100  # to prevent huge queries
