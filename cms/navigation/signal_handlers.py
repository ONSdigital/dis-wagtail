from typing import Any

from django.core.cache import cache
from django.db.models.signals import post_save
from wagtail.models import Site
from wagtail.signals import published

from cms.core.templatetags.page_config_tags import get_base_page_config_cache_key

from .models import FooterMenu, MainMenu, NavigationSettings


def invalidate_base_page_config(**kwargs: Any) -> None:
    cache.delete_many([get_base_page_config_cache_key(site) for site in Site.objects.all()])


def register_signal_handlers() -> None:
    published.connect(invalidate_base_page_config, sender=MainMenu)
    published.connect(invalidate_base_page_config, sender=FooterMenu)
    post_save.connect(invalidate_base_page_config, sender=NavigationSettings)
