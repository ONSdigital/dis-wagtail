from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from behave.runner import Context
    from wagtail.models import Page

    from cms.taxonomy.models import Topic
    from cms.users.models import User


def get_or_create_topic(topic_name: str, topic_cache: dict[str, Topic] | None = None) -> Topic:
    """Get existing topic from cache/database or create a new one."""
    if topic_cache is not None and topic_name in topic_cache:
        return topic_cache[topic_name]

    # Import lazily to avoid Django AppRegistryNotReady during Behave startup.
    from cms.taxonomy.models import Topic  # pylint: disable=import-outside-toplevel
    from cms.taxonomy.tests.factories import TopicFactory  # pylint: disable=import-outside-toplevel

    # Check database first
    topic = Topic.objects.filter(title=topic_name).first()
    if topic is None:
        topic = TopicFactory(title=topic_name)

    if topic_cache is not None:
        topic_cache[topic_name] = topic

    return topic


def str_to_bool(bool_string: str) -> bool:
    """Takes a string argument which indicates a boolean, and returns the corresponding boolean value.
    raises ValueError if input string is not one of the recognized boolean like values.
    """
    if bool_string.lower() in ("yes", "true", "t", "y", "1"):
        return True
    if bool_string.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise ValueError(f"Invalid input: {bool_string}")


def require_request(requests: list[str], predicate: callable, description: str) -> None:
    """Return the first request matching predicate or raise AssertionError."""
    reqs = list(requests)
    for req in reqs:
        if predicate(req):
            return req

    # Build a short sample of what was seen to aid debugging
    sample = ", ".join(f"{getattr(r, 'method', '?')} {getattr(r, 'url', '?')}" for r in reqs)
    total = len(reqs)

    raise AssertionError(
        f"No request matching {description} was captured "
        f"(checked {total} request{'s' if total != 1 else ''}; sample: {sample})"
    )


def get_page_from_context(context: Context, page_str: str) -> Page | None:
    try:
        return context.topic_pages[page_str]
    except AttributeError, KeyError:
        the_page_attr = page_str.lower().replace(" ", "_")
        if not the_page_attr.endswith("_page"):
            the_page_attr += "_page"

        return getattr(context, the_page_attr, None)


def lock_page(the_page: Page, user: User) -> None:
    the_page.locked = True
    the_page.locked_by = user
    the_page.locked_at = timezone.now()
    the_page.save()
