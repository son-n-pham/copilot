"""Pydantic v2 request/response models with validation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class FileResponse(BaseModel):
    """Response model for file information."""

    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    sha256: str = Field(..., description="SHA256 hash of file content")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024000,
                "sha256": "abc123def456...",
            }
        }
    )


class ProcessResult(BaseModel):
    """Processing result information."""

    message: str = Field(..., description="Summary of processing result")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"message": "Processed 1 file and text prompt successfully"}
        }
    )


class ProcessMeta(BaseModel):
    """Metadata about the processing request."""

    received_at: datetime = Field(
        ..., description="ISO 8601 timestamp when request was received"
    )
    duration_ms: int = Field(
        ..., ge=0, description="Processing duration in milliseconds"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal warnings during processing"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "received_at": "2025-01-08T03:15:00.000Z",
                "duration_ms": 125,
                "warnings": [],
            }
        }
    )


class ProcessResponse(BaseModel):
    """Main response model for /v1/process endpoint."""

    id: UUID = Field(..., description="Unique request identifier")
    prompt: Optional[str] = Field(None, description="Original text prompt or null")
    files: List[FileResponse] = Field(
        default_factory=list, description="Information about uploaded files"
    )
    result: ProcessResult = Field(..., description="Processing result")
    meta: ProcessMeta = Field(..., description="Request metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "prompt": "Analyze this document",
                "files": [
                    {
                        "filename": "report.pdf",
                        "content_type": "application/pdf",
                        "size_bytes": 1024000,
                        "sha256": "abc123def456...",
                    }
                ],
                "result": {"message": "Processed 1 file and text prompt successfully"},
                "meta": {
                    "received_at": "2025-01-08T03:15:00.000Z",
                    "duration_ms": 125,
                    "warnings": [],
                },
            }
        }
    )


class ErrorDetail(BaseModel):
    """Error detail information."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Detailed error message")
    value: Optional[str] = Field(
        None, description="Invalid value that caused the error"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: "ErrorInfo" = Field(..., description="Error information")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "At least one of prompt or files required",
                    "details": {
                        "field": "request",
                        "message": "Either prompt text or file uploads must be provided",
                        "value": None,
                    },
                }
            }
        }
    )


class ErrorInfo(BaseModel):
    """Error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[ErrorDetail] = Field(None, description="Additional error details")


class ProcessCopilotRequest(BaseModel):
    """Request model for Copilot processing with optional file uploads."""

    prompt: str = Field(..., description="Text prompt to send to Microsoft 365 Copilot")
    files_to_upload: Optional[List[str]] = Field(
        default=[],
        description="List of file names to upload from Copilot SharePoint folder (e.g., ['report.pdf', 'data.txt']). Partial matching supported.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "Analyze these files",
                "files_to_upload": ["report.pdf", "data.txt"],
            }
        }
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field("ok", description="Service status")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})
