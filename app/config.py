"""Configuration management using Pydantic Settings."""

from typing import List, Set
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # File upload limits
    max_file_size_mb: int = 10
    max_files: int = 3

    # Allowed MIME types for file uploads
    allowed_mime_types: Set[str] = {
        "text/plain",
        "application/pdf",
        "image/png",
        "image/jpeg",
    }

    # CORS configuration
    fastapi_cors_origins: List[str] = []

    # Logging configuration
    log_level: str = "INFO"

    # API configuration
    api_title: str = "Copilot REST API"
    api_description: str = (
        "FastAPI REST API for processing text prompts and file attachments"
    )
    api_version: str = "1.0.0"
    
    # Copilot integration configuration
    copilot_url: str = "https://copilot.cloud.microsoft/?fromCode=cmcv2&redirectId=079013B7710342F5A1FDB755834168FD&auth=2"
    chrome_exe: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir: str = r".\.Playwright\codes"
    downloads_dir: str = r".\.Playwright\downloads"
    copilot_timeout: int = 120  # seconds
    
    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    def parse_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string or list."""
        if not self.fastapi_cors_origins:
            return ["http://localhost:3000", "http://localhost:8080"]  # Default origins

        if isinstance(self.fastapi_cors_origins, str):
            return [
                origin.strip()
                for origin in self.fastapi_cors_origins.split(",")
                if origin.strip()
            ]

        return self.fastapi_cors_origins


# Global settings instance
settings = Settings()
