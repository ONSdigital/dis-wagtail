from datetime import date
from typing import NotRequired, TypedDict, TypeVar

from cms.articles.models import StatisticalArticlePage
from cms.methodology.models import MethodologyPage

T = TypeVar("T")


class InternalArticleDict(TypedDict, total=False):
    internal_page: StatisticalArticlePage
    title: str


class ExternalArticleDict(TypedDict, total=False):
    url: str
    title: str
    description: str
    is_external: bool
    content_type: NotRequired[str]
    release_date: NotRequired[date | None]


class MethodologyDict(TypedDict):
    internal_page: MethodologyPage


ArticleDict = InternalArticleDict | ExternalArticleDict
