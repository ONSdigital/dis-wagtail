from wagtail.snippets.models import register_snippet

from .viewsets import DatavisViewSetGroup

register_snippet(DatavisViewSetGroup)
