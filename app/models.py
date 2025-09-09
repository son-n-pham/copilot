"""Internal data models and enums."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List


class ErrorCode(str, Enum):
    """Error codes for API responses."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    TOO_MANY_FILES = "TOO_MANY_FILES"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class FileInfo:
    """Information about an uploaded file."""

    filename: str
    content_type: str
    size_bytes: int
    sha256: str


@dataclass
class ProcessingResult:
    """Result of processing a request."""

    message: str
    file_count: int = 0
    has_prompt: bool = False
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
