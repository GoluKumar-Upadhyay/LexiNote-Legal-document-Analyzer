from typing import Any

from pydantic import BaseModel, Field


class MetaInfo(BaseModel):
    provider_used: str | None = None
    warnings: list[str] = Field(default_factory=list)
    fallback: bool | None = None
    chunk_count: int | None = None


class UploadResponse(BaseModel):
    confidence: str
    extracted_text: str
    predicted_category: str
    reason: str
    suggested_action: str
    can_generate_summary: bool = True
    expected_documents: list[str] = Field(default_factory=list)
    meta: MetaInfo | dict[str, Any] = Field(default_factory=dict, alias="_meta")


class MindMapRequest(BaseModel):
    category: str = "citizen"
    summary_json: dict[str, Any]


class VideoResponse(BaseModel):
    video_path: str
    storyboard: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict, alias="_meta")
