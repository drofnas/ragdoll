from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UsageLimitSet(BaseModel):
    documents: int | None = None
    max_file_size_bytes: int | None = None
    chunks: int | None = None
    storage_bytes: int | None = None
    tokens_5h: int | None = None
    tokens_week: int | None = None
    retrieval_chunks: int | None = None
    output_tokens: int | None = None
    per_document_chunks: int | None = None


class UsageAmounts(BaseModel):
    documents: int = 0
    chunks: int = 0
    storage_bytes: int = 0
    tokens_5h: int = 0
    tokens_week: int = 0


class UsagePercentages(BaseModel):
    documents: float | None = None
    chunks: float | None = None
    storage_bytes: float | None = None
    tokens_5h: float | None = None
    tokens_week: float | None = None


class UsageResetTimers(BaseModel):
    tokens_5h_resets_at: datetime | None = None
    tokens_week_resets_at: datetime | None = None


class UsageStatusFlags(BaseModel):
    chat_blocked: bool = False
    upload_blocked: bool = False
    partially_indexed_documents: int = 0


class UsageSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usage: UsageAmounts
    limits: UsageLimitSet
    percent_used: UsagePercentages
    resets_at: UsageResetTimers
    status: UsageStatusFlags
