from django.http import Http404
from wagtail.admin.views.pages.bulk_actions import PublishBulkAction as CorePublishBulkAction
from wagtail.models import Page


class PublishBulkAction(CorePublishBulkAction):
    @classmethod
    def get_queryset(cls, model: Page, object_ids: list[int | str]) -> list[Page]:
        # TODO: remove when https://github.com/wagtail/wagtail/issues/13976 is fixed
        # ensure we use the specific pages
        pages = Page.objects.filter(pk__in=object_ids).specific(defer=True)

        if not pages:
            raise Http404("No Page matches the given query.")

        return list(pages)
