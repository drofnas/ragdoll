from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class MutationResult(BaseModel):
    success: bool = Field(default=True)
    message: str | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={"example": {"success": True, "message": "Updated successfully."}}
    )


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)


class ProblemEnvelope(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str | None = None
