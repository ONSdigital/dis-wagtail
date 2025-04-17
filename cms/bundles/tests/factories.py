import factory
from django.utils import timezone

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundlePage
from cms.users.tests.factories import UserFactory


class BundleFactory(factory.django.DjangoModelFactory):
    """Factory for Bundle model."""

    class Meta:
        model = Bundle

    name = factory.Faker("sentence", nb_words=4)
    created_at = factory.LazyFunction(timezone.now)
    created_by = factory.SubFactory(UserFactory)
    status = BundleStatus.DRAFT

    class Params:
        """Defines custom factory traits.

        Usage: BundlFactory(approved=True) or BundlFactory(published=True)
        """

        in_review = factory.Trait(
            status=BundleStatus.IN_REVIEW,
            publication_date=factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=1)),
        )

        approved = factory.Trait(
            status=BundleStatus.APPROVED,
            approved_at=factory.LazyFunction(timezone.now),
            approved_by=factory.SubFactory(UserFactory),
            publication_date=factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=1)),
        )

        published = factory.Trait(
            status=BundleStatus.PUBLISHED,
            approved_at=factory.LazyFunction(lambda: timezone.now() - timezone.timedelta(days=1)),
            approved_by=factory.SubFactory(UserFactory),
            publication_date=factory.LazyFunction(timezone.now),
        )

    @factory.post_generation
    def bundled_pages(self, create, extracted, **kwargs):
        """Creates BundlePage instances for the bundle.

        Usage:
            # Create a bundle with no pages
            bundle = BundleFactory()

            # Create a bundle with specific pages
            bundle = BundleFactory(bundled_pages=[page1, page2])

            # Create an approved bundle with pages
            bundle = BundleFactory(approved=True, bundled_pages=[page1, page2])
        """
        if not create:
            return

        if extracted:
            for page in extracted:
                BundlePageFactory(parent=self, page=page)


class BundlePageFactory(factory.django.DjangoModelFactory):
    """Factory for BundlePage orderable model."""

    class Meta:
        model = BundlePage

    parent = factory.SubFactory(BundleFactory)
    page = factory.SubFactory("cms.articles.tests.factories.StatisticalArticlePageFactory")
    sort_order = factory.Sequence(lambda n: n)
