from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(json_schema_extra={"example": {"page": 1, "page_size": 20}})

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def resolve_pagination_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
