import datetime
from typing import TypedDict, TypeVar

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
    content_type: RelatedContentType
    release_date: datetime.date | None
    is_external: bool


class InternalMethodologyDict(TypedDict, total=False):
    internal_page: MethodologyPage
    title: str


ArticleDict = InternalArticleDict | ExternalArticleDict
MethodologyDict = InternalMethodologyDict | ExternalArticleDict
