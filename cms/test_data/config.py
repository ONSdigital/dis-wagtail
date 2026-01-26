from typing import Annotated, Self

import annotated_types
from faker import Faker
from pydantic import BaseModel, NonNegativeInt, PositiveInt, model_validator

FractionalFloat = Annotated[float, annotated_types.Ge(0), annotated_types.Le(1)]


class RangeConfig(BaseModel):
    min: NonNegativeInt = 1
    max: PositiveInt

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.min == self.max:
            raise ValueError("Range is unnecessary")
        if self.min > self.max:
            raise ValueError("min must be less than max")
        return self


class ModelCreationConfig(BaseModel):
    count: NonNegativeInt | RangeConfig = 1


class PageCreationConfig(ModelCreationConfig):
    published_probability: FractionalFloat = 0.5
    revisions: NonNegativeInt | RangeConfig = 0


class TopicCreationConfig(PageCreationConfig):
    datasets: NonNegativeInt | RangeConfig = 1
    dataset_manual_links: NonNegativeInt = 0
    explore_more: NonNegativeInt | RangeConfig = 1


class TestDataConfig(BaseModel):
    datasets: ModelCreationConfig = ModelCreationConfig()
    images: ModelCreationConfig = ModelCreationConfig()
    topics: TopicCreationConfig = TopicCreationConfig(count=3)

    def get_count(self, data: int | RangeConfig, faker: Faker) -> int:
        if isinstance(data, int):
            return data

        return faker.random_int(min=data.min, max=data.max)
