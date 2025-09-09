"""API endpoints for /v1/process and /v1/health."""

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas import (
    ProcessResponse,
    HealthResponse,
    ErrorResponse,
    FileResponse,
    ProcessResult,
    ProcessMeta,
    ProcessCopilotRequest,
)
from app.services.processor import processor, ValidationError
from app.services.copilot_client import copilot_client, CopilotClientError
from app.models import ErrorCode


router = APIRouter()


def create_error_response(
    status_code: int,
    error_code: ErrorCode,
    message: str,
    field: Optional[str] = None,
    value: Optional[str] = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        error_code: Application error code
        message: Error message
        field: Field that caused the error (optional)
        value: Invalid value (optional)

    Returns:
        JSONResponse with error details
    """
    error_detail = None
    if field is not None:
        error_detail = {"field": field, "message": message, "value": value}

    error_response = ErrorResponse(
        error={"code": error_code.value, "message": message, "details": error_detail}
    )

    return JSONResponse(status_code=status_code, content=error_response.model_dump())


@router.post(
    "/v1/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process text prompt and/or file uploads",
    description="""
    Accepts user input as text, file(s), or both and returns processed metadata and an echo-style result.
    
    - **prompt**: Optional text input 
    - **files**: Optional file uploads (0-3 files, max 10MB each)
    - At least one of prompt or files must be provided
    - Supported file types: text/plain, application/pdf, image/png, image/jpeg
    """,
    responses={
        200: {"description": "Successfully processed request"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def process_request(
    prompt: Optional[str] = Form(None, description="Text prompt to process"),
    files: List[UploadFile] = File(
        default=[], description="Files to upload and process"
    ),
):
    """Process text prompt and/or file uploads."""
    start_time = time.time()
    request_id = uuid.uuid4()
    received_at = datetime.now(timezone.utc)

    try:
        # Process the request
        file_infos, processing_result = await processor.process_request(prompt, files)

        # Calculate processing duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Convert file infos to response format
        file_responses = [
            FileResponse(
                filename=info.filename,
                content_type=info.content_type,
                size_bytes=info.size_bytes,
                sha256=info.sha256,
            )
            for info in file_infos
        ]

        # Create response
        response = ProcessResponse(
            id=request_id,
            prompt=prompt if prompt and prompt.strip() else None,
            files=file_responses,
            result=ProcessResult(message=processing_result.message),
            meta=ProcessMeta(
                received_at=received_at,
                duration_ms=duration_ms,
                warnings=processing_result.warnings,
            ),
        )

        return response

    except ValidationError as e:
        # Map validation errors to appropriate HTTP status codes
        if e.code == ErrorCode.UNSUPPORTED_MEDIA_TYPE:
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        elif e.code == ErrorCode.TOO_MANY_FILES or e.code == ErrorCode.FILE_TOO_LARGE:
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return create_error_response(
            status_code=status_code, error_code=e.code, message=e.message, field=e.field
        )

    except Exception as e:
        # Handle unexpected errors
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred while processing the request",
        )


@router.post(
    "/v1/process/copilot",
    response_model=ProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process text prompt using Microsoft 365 Copilot",
    description="""
    Sends a text prompt to Microsoft 365 Copilot via Playwright automation and returns the actual response.
    
    **Requirements:**
    - Chrome browser must be installed at the configured path
    - User must be logged into Microsoft 365 Copilot in Chrome (persistent profile)
    - Supports optional file uploads from Copilot SharePoint folder
    
    **Note:** This endpoint launches Chrome, navigates to Copilot, optionally uploads files,
    sends the prompt, waits for the response, and extracts the reply. Response time is typically 30-120 seconds.
    """,
    responses={
        200: {"description": "Successfully processed request with Copilot response"},
        400: {
            "model": ErrorResponse,
            "description": "Validation error or missing prompt",
        },
        500: {
            "model": ErrorResponse,
            "description": "Copilot service error or browser issues",
        },
        503: {"model": ErrorResponse, "description": "Copilot service unavailable"},
    },
)
async def process_with_copilot(request: ProcessCopilotRequest):
    """Process text prompt using Microsoft 365 Copilot via Playwright automation."""
    start_time = time.time()
    request_id = uuid.uuid4()
    received_at = datetime.now(timezone.utc)

    try:
        # Validate prompt
        if not request.prompt or not request.prompt.strip():
            return create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Prompt is required and cannot be empty",
                field="prompt",
            )

        # Send prompt to Copilot and get response
        copilot_response = await copilot_client.send_prompt_and_get_response(
            request.prompt.strip(),
            files_to_upload=request.files_to_upload or [],
            timeout=120,  # 2 minute timeout
        )

        # Calculate processing duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Create response
        response = ProcessResponse(
            id=request_id,
            prompt=request.prompt.strip(),
            files=[],  # Copilot endpoint doesn't return file metadata for uploaded files
            result=ProcessResult(message=copilot_response),
            meta=ProcessMeta(
                received_at=received_at,
                duration_ms=duration_ms,
                warnings=[],
            ),
        )

        return response

    except CopilotClientError as e:
        # Handle Copilot-specific errors
        if "login" in str(e).lower() or "not respond" in str(e).lower():
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return create_error_response(
            status_code=status_code,
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"Copilot service error: {str(e)}",
        )

    except Exception:
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred while processing the request",
        )

    except Exception:
        # Handle unexpected errors
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred while processing with Copilot",
        )


@router.get(
    "/v1/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Returns service health status for readiness/liveness checks.",
)
async def health_check():
    """Health check endpoint for monitoring and load balancing."""
    return HealthResponse(status="ok")


@router.get(
    "/v1/copilot/status",
    status_code=status.HTTP_200_OK,
    summary="Copilot session status",
    description="Returns the current status of the persistent Copilot session.",
)
async def copilot_status():
    """Get the current status of the persistent Copilot session."""
    status_info = copilot_client.get_status()
    return {
        "copilot_session": status_info,
        "message": "Ready for requests"
        if status_info["is_ready"]
        else "Session not ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
