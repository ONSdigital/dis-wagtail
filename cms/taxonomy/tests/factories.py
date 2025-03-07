import factory.enums
from factory import Factory, faker, post_generation

from cms.taxonomy.models import Topic


class TopicFactory(Factory):
    class Meta:
        model = Topic
        strategy = factory.BUILD_STRATEGY  # To prevent Factory from trying to save the node

    id: str = faker.Faker("random_number", digits=50, fix_len=True)  # Use a very long ID for uniqueness
    title: str = faker.Faker("sentence", nb_words=3)
    description: str = faker.Faker("sentence", nb_words=10)

    @post_generation
    def save_topic_in_tree(obj: Topic, *_args, **_kwargs) -> None:
        """New topics need to be saved with save_topic, so we use the BUILD_STRATEGY to skip the automatic save,
        and instead save the obj ourselves in this post generation hook.
        """
        Topic.save_new(obj)
