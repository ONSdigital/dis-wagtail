from typing import TYPE_CHECKING

from django.urls import reverse
from wagtail.test.utils.form_data import inline_formset, nested_form_data, rich_text, streamfield

from cms.taxonomy.models import Topic

if TYPE_CHECKING:
    from django.test import Client


def post_page_add_form_to_create_topic_page(client: Client, homepage_id: int) -> None:
    topic_term = Topic(id="topic-a", title="Topic A")
    Topic.save_new(topic_term)

    data = nested_form_data(
        {
            "title": "Topic page",
            "slug": "topic-page",
            "summary": rich_text("test"),
            "headline_figures": streamfield([]),
            "datasets": streamfield([]),
            "time_series": streamfield([]),
            "related_articles": inline_formset([]),
            "related_methodologies": inline_formset([]),
            "explore_more": streamfield([]),
            "topic": topic_term.pk,
        }
    )
    client.post(reverse("wagtailadmin_pages:add", args=["topics", "topicpage", homepage_id]), data=data)
