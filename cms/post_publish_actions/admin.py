from django.conf import settings
from django.contrib import admin

from .models import PostPublishAction

if settings.WAGTAIL_CORE_ADMIN_LOGIN_ENABLED:
    admin.site.register(PostPublishAction)
