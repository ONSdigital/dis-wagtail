from datetime import date
from typing import NotRequired, TypedDict, TypeVar

from cms.articles.models import StatisticalArticlePage
from cms.core.enums import RelatedContentType
from cms.methodology.models import MethodologyPage

T = TypeVar("T")


class InternalArticleDict(TypedDict, total=False):
    internal_page: StatisticalArticlePage
    title: str


class ExternalArticleDict(TypedDict):
    url: str
    title: str
    description: str
    is_external: bool
    content_type: NotRequired[RelatedContentType]
    release_date: NotRequired[date | None]


class InternalMethodologyDict(TypedDict, total=False):
    internal_page: MethodologyPage
    title: str


ArticleDict = InternalArticleDict | ExternalArticleDict
MethodologyDict = InternalMethodologyDict | ExternalArticleDict
