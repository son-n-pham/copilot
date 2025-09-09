"""Shared test fixtures and configuration."""

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    content = "This is a test text file.\nIt has multiple lines.\nFor testing purposes."
    return io.BytesIO(content.encode("utf-8"))


@pytest.fixture
def sample_large_file():
    """Create a large file for size limit testing."""
    # Create a 15MB file (larger than 10MB limit)
    content = b"x" * (15 * 1024 * 1024)
    return io.BytesIO(content)


@pytest.fixture
def sample_pdf_content():
    """Create minimal PDF content for testing."""
    # Minimal PDF file content (valid PDF header)
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
181
%%EOF"""
    return io.BytesIO(pdf_content)


@pytest.fixture
def sample_image_content():
    """Create minimal PNG content for testing."""
    # Minimal PNG file (1x1 transparent pixel)
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    return io.BytesIO(png_content)


@pytest.fixture
def invalid_file_content():
    """Create content that doesn't match any allowed MIME type."""
    # Create content that looks like an executable
    content = b"\x4d\x5a\x90\x00"  # DOS header for .exe file
    return io.BytesIO(content)
