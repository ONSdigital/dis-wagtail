import uuid

from django.test import TestCase
from wagtail.models import ReferenceIndex

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.datavis.models import RenderedChartImage
from cms.datavis.tests.factories import RenderedChartImageFactory, TableDataFactory


def chart_block(image_pk):
    return {
        "type": "line_chart",
        "id": str(uuid.uuid4()),
        "value": {
            "title": "Test Chart",
            "audio_description": "Description",
            "table": TableDataFactory(),
            "theme": "primary",
            "rendered_chart_image": image_pk,
        },
    }


class RenderedChartImageReferenceTests(TestCase):
    """The privacy machinery keys off references, so the image must be discoverable as one."""

    def setUp(self):
        self.image = RenderedChartImageFactory()
        page = StatisticalArticlePageFactory()
        page.content = [
            {
                "type": "section",
                "id": str(uuid.uuid4()),
                "value": {"title": "Section", "content": [chart_block(self.image.pk)]},
            }
        ]
        page.featured_chart = [chart_block(self.image.pk)]
        page.save()
        self.page = StatisticalArticlePage.objects.get(pk=page.pk)

    def test_image_is_recorded_in_the_reference_index(self):
        ReferenceIndex.create_or_update_for_object(self.page)

        self.assertTrue(
            ReferenceIndex.objects.filter(
                to_content_type__app_label="datavis",
                to_content_type__model="renderedchartimage",
                to_object_id=str(self.image.pk),
            ).exists()
        )

    def test_image_in_content_is_returned_by_get_referenced_asset_ids(self):
        self.assertIn(str(self.image.pk), self.page.get_referenced_asset_ids(RenderedChartImage))
