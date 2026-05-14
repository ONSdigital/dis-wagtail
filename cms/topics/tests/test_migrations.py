from collections.abc import Sequence
from datetime import date, datetime
from typing import ClassVar

from cms.core.tests import MigrationTestCase
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.taxonomy.tests.factories import TopicFactory
from cms.topics.tests.factories import (
    TopicPageFactory,
    TopicPageRelatedMethodologyFactory,
)


class TestMigration0009Rollback(MigrationTestCase):
    app = "topics"
    previous_migration: ClassVar[Sequence[tuple[str, str]]] = [("topics", "0008_topicpage_time_series")]
    next_migration: ClassVar[Sequence[tuple[str, str]]] = [
        ("topics", "0009_topicpagerelatedmethodology_content_type_and_more")
    ]

    def test_rollback(self):
        # Setup on latest version
        HomePage.objects.first()
        TopicFactory()
        topic_page = TopicPageFactory(title="Test Topic")
        methodology = MethodologyPageFactory(parent__parent=topic_page, publication_date=datetime(2024, 6, 1))
        TopicPageRelatedMethodologyFactory(page=methodology)
        TopicPageRelatedMethodologyFactory(
            parent=topic_page,
            page=None,
            external_url="https://ons.gov.uk",
            title="External Methodology",
            description="desc",
            release_date=date.today(),
        )
        TopicPageRelatedMethodologyFactory(
            parent=topic_page,
            page=None,
            external_url="https://ons.gov.uk",
            title="External Methodology Two",
            description="desc",
            release_date=date.today(),
        )

        # Rollback
        self.migrate_to(self.previous_migration)

        # Checks
        # Shouldn't get any integrity errors and should have cleaned up the related methodologies without pages
        RelatedMethodology = self.get_model(self.app, "TopicPageRelatedMethodology")  # pylint: disable=C0103
        related = RelatedMethodology.objects.all()
        self.assertEqual(related.count(), 1)
