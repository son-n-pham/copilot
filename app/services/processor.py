"""Core validation and processing logic for file uploads and text prompts."""

import io
from typing import List, Optional, Tuple
from fastapi import UploadFile, HTTPException

try:
    import magic
except ImportError:
    magic = None

from app.config import settings
from app.models import FileInfo, ProcessingResult, ErrorCode
from app.utils.hash import compute_sha256_stream


class ValidationError(Exception):
    """Custom validation error."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        field: Optional[str] = None,
    ):
        self.message = message
        self.code = code
        self.field = field
        super().__init__(message)


class ProcessorService:
    """Service for validating and processing requests."""

    def __init__(self):
        self.max_file_size_bytes = settings.get_max_file_size_bytes()
        self.max_files = settings.max_files
        self.allowed_mime_types = settings.allowed_mime_types

    def validate_request(self, prompt: Optional[str], files: List[UploadFile]) -> None:
        """
        Validate the overall request.

        Args:
            prompt: Text prompt (optional)
            files: List of uploaded files (optional)

        Raises:
            ValidationError: If validation fails
        """
        # Check that at least one input is provided
        if not prompt and not files:
            raise ValidationError(
                "At least one of prompt or files required",
                ErrorCode.VALIDATION_ERROR,
                "request",
            )

        # Check file count limit
        if len(files) > self.max_files:
            raise ValidationError(
                f"Too many files. Maximum {self.max_files} files allowed, got {len(files)}",
                ErrorCode.TOO_MANY_FILES,
                "files",
            )

    def validate_file(self, file: UploadFile) -> None:
        """
        Validate a single uploaded file.

        Args:
            file: Uploaded file to validate

        Raises:
            ValidationError: If validation fails
        """
        # Check file size (this is approximate, we'll check exact size when reading)
        if hasattr(file, "size") and file.size and file.size > self.max_file_size_bytes:
            raise ValidationError(
                f"File '{file.filename}' is too large. Maximum size: {settings.max_file_size_mb}MB",
                ErrorCode.FILE_TOO_LARGE,
                "files",
            )

        # Validate content type if provided by client
        if file.content_type and file.content_type not in self.allowed_mime_types:
            raise ValidationError(
                f"Unsupported content type '{file.content_type}' for file '{file.filename}'. "
                f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}",
                ErrorCode.UNSUPPORTED_MEDIA_TYPE,
                "files",
            )

    def detect_mime_type(self, file_content: bytes, filename: str) -> str:
        """
        Detect MIME type using server-side content analysis.

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Detected MIME type
        """
        if magic is not None:
            try:
                mime_type = magic.from_buffer(file_content, mime=True)
                return mime_type
            except Exception:
                pass

        # Fallback to simple extension-based detection
        extension = filename.lower().split(".")[-1] if "." in filename else ""
        extension_map = {
            "txt": "text/plain",
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        return extension_map.get(extension, "application/octet-stream")

    async def process_file(self, file: UploadFile) -> FileInfo:
        """
        Process a single uploaded file.

        Args:
            file: Uploaded file to process

        Returns:
            FileInfo object with file metadata

        Raises:
            ValidationError: If file processing fails
        """
        try:
            # Read file content
            file_content = await file.read()

            # Check actual file size
            if len(file_content) > self.max_file_size_bytes:
                raise ValidationError(
                    f"File '{file.filename}' is too large. Maximum size: {settings.max_file_size_mb}MB",
                    ErrorCode.FILE_TOO_LARGE,
                    "files",
                )

            # Detect MIME type from content
            detected_mime_type = self.detect_mime_type(
                file_content, file.filename or "unknown"
            )

            # Validate detected MIME type
            if detected_mime_type not in self.allowed_mime_types:
                raise ValidationError(
                    f"Unsupported file type '{detected_mime_type}' detected for file '{file.filename}'. "
                    f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}",
                    ErrorCode.UNSUPPORTED_MEDIA_TYPE,
                    "files",
                )

            # Compute SHA256 hash
            file_stream = io.BytesIO(file_content)
            sha256_hash = compute_sha256_stream(file_stream)

            return FileInfo(
                filename=file.filename or "unknown",
                content_type=detected_mime_type,
                size_bytes=len(file_content),
                sha256=sha256_hash,
            )

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Failed to process file '{file.filename}': {str(e)}",
                ErrorCode.INTERNAL_ERROR,
                "files",
            )

    async def process_request(
        self, prompt: Optional[str], files: List[UploadFile]
    ) -> Tuple[List[FileInfo], ProcessingResult]:
        """
        Process the complete request.

        Args:
            prompt: Text prompt (optional)
            files: List of uploaded files (optional)

        Returns:
            Tuple of (file_info_list, processing_result)

        Raises:
            ValidationError: If processing fails
        """
        # Validate overall request
        self.validate_request(prompt, files)

        # Process each file
        file_infos = []
        warnings = []

        for file in files:
            try:
                self.validate_file(file)
                file_info = await self.process_file(file)
                file_infos.append(file_info)
            except ValidationError as e:
                if e.code == ErrorCode.UNSUPPORTED_MEDIA_TYPE:
                    warnings.append(f"Skipped file '{file.filename}': {e.message}")
                    continue
                else:
                    raise

        # Create processing result
        file_count = len(file_infos)
        has_prompt = bool(prompt and prompt.strip())

        if file_count == 0 and not has_prompt:
            raise ValidationError(
                "No valid files processed and no prompt provided",
                ErrorCode.VALIDATION_ERROR,
                "request",
            )

        # Generate result message
        parts = []
        if file_count > 0:
            parts.append(f"{file_count} file{'s' if file_count != 1 else ''}")
        if has_prompt:
            parts.append("text prompt")

        message = f"Processed {' and '.join(parts)} successfully"

        result = ProcessingResult(
            message=message,
            file_count=file_count,
            has_prompt=has_prompt,
            warnings=warnings,
        )

        return file_infos, result


# Global processor instance
processor = ProcessorService()
