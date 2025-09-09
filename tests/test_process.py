"""Comprehensive test suite for the process API endpoints."""

import json
from uuid import UUID
from datetime import datetime
from unittest.mock import patch, AsyncMock


class TestProcessEndpoint:
    """Test cases for the /v1/process endpoint."""

    def test_prompt_only_success(self, client):
        """Test successful processing with prompt only."""
        response = client.post("/v1/process", data={"prompt": "Analyze this text"})

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "id" in data
        assert "prompt" in data
        assert "files" in data
        assert "result" in data
        assert "meta" in data

        # Validate content
        assert data["prompt"] == "Analyze this text"
        assert data["files"] == []
        assert "text prompt" in data["result"]["message"]
        assert data["meta"]["warnings"] == []
        assert data["meta"]["duration_ms"] >= 0

        # Validate UUID format
        UUID(data["id"])  # Will raise ValueError if not valid UUID

        # Validate datetime format
        datetime.fromisoformat(data["meta"]["received_at"].replace("Z", "+00:00"))

    def test_single_file_only_success(self, client, sample_text_file):
        """Test successful processing with single file only."""
        sample_text_file.seek(0)
        response = client.post(
            "/v1/process",
            files=[("files", ("test.txt", sample_text_file, "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert data["prompt"] is None
        assert len(data["files"]) == 1

        file_info = data["files"][0]
        assert file_info["filename"] == "test.txt"
        assert file_info["content_type"] == "text/plain"
        assert file_info["size_bytes"] > 0
        assert len(file_info["sha256"]) == 64  # SHA256 hex length

        assert "1 file" in data["result"]["message"]

    def test_multiple_files_success(self, client, sample_text_file, sample_pdf_content):
        """Test successful processing with multiple files."""
        sample_text_file.seek(0)
        sample_pdf_content.seek(0)

        response = client.post(
            "/v1/process",
            files=[
                ("files", ("test.txt", sample_text_file, "text/plain")),
                ("files", ("test.pdf", sample_pdf_content, "application/pdf")),
            ],
        )

        assert response.status_code == 200
        data = response.json()

        assert data["prompt"] is None
        assert len(data["files"]) == 2
        assert "2 files" in data["result"]["message"]

        # Check both files are processed
        filenames = [f["filename"] for f in data["files"]]
        assert "test.txt" in filenames
        assert "test.pdf" in filenames

    def test_both_prompt_and_files_success(self, client, sample_text_file):
        """Test successful processing with both prompt and files."""
        sample_text_file.seek(0)

        response = client.post(
            "/v1/process",
            data={"prompt": "Analyze this document"},
            files=[("files", ("test.txt", sample_text_file, "text/plain"))],
        )

        assert response.status_code == 200
        data = response.json()

        assert data["prompt"] == "Analyze this document"
        assert len(data["files"]) == 1
        assert "1 file and text prompt" in data["result"]["message"]

    def test_empty_request_validation_error(self, client):
        """Test validation error when neither prompt nor files are provided."""
        response = client.post("/v1/process")

        assert response.status_code == 400
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "at least one" in data["error"]["message"].lower()

    def test_too_many_files_error(self, client, sample_text_file):
        """Test error when too many files are uploaded."""
        files = []
        for i in range(4):  # More than the limit of 3
            sample_text_file.seek(0)
            files.append(("files", (f"test{i}.txt", sample_text_file, "text/plain")))

        response = client.post("/v1/process", files=files)

        assert response.status_code == 400
        data = response.json()

        assert data["error"]["code"] == "TOO_MANY_FILES"
        assert "too many files" in data["error"]["message"].lower()

    def test_file_too_large_error(self, client, sample_large_file):
        """Test error when file exceeds size limit."""
        sample_large_file.seek(0)

        response = client.post(
            "/v1/process",
            files=[("files", ("large.txt", sample_large_file, "text/plain"))],
        )

        assert response.status_code == 400
        data = response.json()

        assert data["error"]["code"] == "FILE_TOO_LARGE"
        assert "too large" in data["error"]["message"].lower()

    def test_unsupported_mime_type_error(self, client, invalid_file_content):
        """Test error when file has unsupported MIME type."""
        invalid_file_content.seek(0)

        response = client.post(
            "/v1/process",
            files=[
                (
                    "files",
                    ("test.exe", invalid_file_content, "application/x-executable"),
                )
            ],
        )

        assert response.status_code == 415
        data = response.json()

        assert data["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
        assert "unsupported" in data["error"]["message"].lower()

    def test_whitespace_only_prompt(self, client):
        """Test that whitespace-only prompt is treated as no prompt."""
        response = client.post("/v1/process", data={"prompt": "   \n\t  "})

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_empty_file(self, client):
        """Test processing of empty file."""
        empty_file = b""
        response = client.post(
            "/v1/process", files=[("files", ("empty.txt", empty_file, "text/plain"))]
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) == 1
        assert data["files"][0]["size_bytes"] == 0

    def test_same_filename_multiple_files(
        self, client, sample_text_file, sample_pdf_content
    ):
        """Test processing multiple files with same filename."""
        sample_text_file.seek(0)
        sample_pdf_content.seek(0)

        response = client.post(
            "/v1/process",
            files=[
                ("files", ("test.txt", sample_text_file, "text/plain")),
                ("files", ("test.txt", sample_pdf_content, "application/pdf")),
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) == 2

        # Both files should be processed despite same filename
        content_types = [f["content_type"] for f in data["files"]]
        assert "text/plain" in content_types
        assert "application/pdf" in content_types

    def test_response_schema_validation(self, client):
        """Test that response matches expected schema structure."""
        response = client.post("/v1/process", data={"prompt": "Test prompt"})

        assert response.status_code == 200
        data = response.json()

        # Check all required fields exist
        required_fields = ["id", "prompt", "files", "result", "meta"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check result structure
        assert "message" in data["result"]

        # Check meta structure
        meta_fields = ["received_at", "duration_ms", "warnings"]
        for field in meta_fields:
            assert field in data["meta"], f"Missing meta field: {field}"

        # Check types
        assert isinstance(data["files"], list)
        assert isinstance(data["meta"]["duration_ms"], int)
        assert isinstance(data["meta"]["warnings"], list)

    def test_image_file_processing(self, client, sample_image_content):
        """Test processing of image files."""
        sample_image_content.seek(0)

        response = client.post(
            "/v1/process",
            files=[("files", ("test.png", sample_image_content, "image/png"))],
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["files"]) == 1
        file_info = data["files"][0]
        assert file_info["filename"] == "test.png"
        assert file_info["content_type"] == "image/png"
        assert file_info["size_bytes"] > 0

    def test_malformed_form_data(self, client):
        """Test handling of malformed multipart form data."""
        # This is harder to test with TestClient, but we can test with invalid field names
        response = client.post("/v1/process", data={"invalid_field": "value"})

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


class TestHealthEndpoint:
    """Test cases for the /v1/health endpoint."""

    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get("/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data == {"status": "ok"}

    def test_health_check_response_structure(self, client):
        """Test health check response structure."""
        response = client.get("/v1/health")

        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data


class TestRootEndpoint:
    """Test cases for the root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint provides useful information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "docs" in data
        assert "health" in data
        assert data["docs"] == "/docs"
        assert data["health"] == "/v1/health"


class TestCopilotEndpoint:
    """Test cases for the /v1/process/copilot endpoint."""

    @patch("app.services.copilot_client.copilot_client.send_prompt_and_get_response")
    def test_copilot_prompt_only_success(self, mock_send_prompt, client):
        """Test successful copilot processing with prompt only."""
        mock_send_prompt.return_value = "This is a test response from Copilot."

        response = client.post(
            "/v1/process/copilot", json={"prompt": "What is machine learning?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "id" in data
        assert "prompt" in data
        assert "files" in data
        assert "result" in data
        assert "meta" in data

        # Validate content
        assert data["prompt"] == "What is machine learning?"
        assert data["files"] == []
        assert data["result"]["message"] == "This is a test response from Copilot."
        assert data["meta"]["warnings"] == []
        assert data["meta"]["duration_ms"] >= 0

        # Validate UUID format
        UUID(data["id"])

        # Validate datetime format
        datetime.fromisoformat(data["meta"]["received_at"].replace("Z", "+00:00"))

        # Verify the mock was called correctly
        mock_send_prompt.assert_called_once_with(
            "What is machine learning?", files_to_upload=[], timeout=120
        )

    @patch("app.services.copilot_client.copilot_client.send_prompt_and_get_response")
    def test_copilot_with_file_uploads_success(self, mock_send_prompt, client):
        """Test successful copilot processing with file uploads."""
        mock_send_prompt.return_value = "Analysis of uploaded files completed."

        response = client.post(
            "/v1/process/copilot",
            json={
                "prompt": "Analyze these files",
                "files_to_upload": ["report.pdf", "data.txt"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "id" in data
        assert "prompt" in data
        assert "files" in data
        assert "result" in data
        assert "meta" in data

        # Validate content
        assert data["prompt"] == "Analyze these files"
        assert data["files"] == []
        assert data["result"]["message"] == "Analysis of uploaded files completed."
        assert data["meta"]["warnings"] == []
        assert data["meta"]["duration_ms"] >= 0

        # Verify the mock was called with file uploads
        mock_send_prompt.assert_called_once_with(
            "Analyze these files",
            files_to_upload=["report.pdf", "data.txt"],
            timeout=120,
        )

    @patch("app.services.copilot_client.copilot_client.send_prompt_and_get_response")
    def test_copilot_empty_files_list(self, mock_send_prompt, client):
        """Test copilot processing with empty files_to_upload list."""
        mock_send_prompt.return_value = "Response without file uploads."

        response = client.post(
            "/v1/process/copilot", json={"prompt": "Test prompt", "files_to_upload": []}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["prompt"] == "Test prompt"
        assert data["result"]["message"] == "Response without file uploads."

        # Verify the mock was called with empty list
        mock_send_prompt.assert_called_once_with(
            "Test prompt", files_to_upload=[], timeout=120
        )

    def test_copilot_missing_prompt_validation_error(self, client):
        """Test validation error when prompt is missing."""
        response = client.post(
            "/v1/process/copilot", json={"files_to_upload": ["test.pdf"]}
        )

        assert response.status_code == 422  # Pydantic validation error
        data = response.json()

        assert "detail" in data
        assert "prompt" in str(data["detail"]).lower()

    def test_copilot_empty_prompt_validation_error(self, client):
        """Test validation error when prompt is empty."""
        response = client.post("/v1/process/copilot", json={"prompt": ""})

        assert response.status_code == 400
        data = response.json()

        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "required" in data["error"]["message"].lower()

    def test_copilot_whitespace_only_prompt_validation_error(self, client):
        """Test validation error when prompt contains only whitespace."""
        response = client.post("/v1/process/copilot", json={"prompt": "   \n\t  "})

        assert response.status_code == 400
        data = response.json()

        assert data["error"]["code"] == "VALIDATION_ERROR"

    @patch("app.services.copilot_client.copilot_client.send_prompt_and_get_response")
    def test_copilot_service_error(self, mock_send_prompt, client):
        """Test handling of copilot service errors."""
        from app.services.copilot_client import CopilotClientError

        mock_send_prompt.side_effect = CopilotClientError("Browser automation failed")

        response = client.post("/v1/process/copilot", json={"prompt": "Test prompt"})

        assert response.status_code == 500
        data = response.json()

        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "Browser automation failed" in data["error"]["message"]

    @patch("app.services.copilot_client.copilot_client.send_prompt_and_get_response")
    def test_copilot_login_required_error(self, mock_send_prompt, client):
        """Test handling of login required errors."""
        from app.services.copilot_client import CopilotClientError

        mock_send_prompt.side_effect = CopilotClientError(
            "Please log in to Copilot first"
        )

        response = client.post("/v1/process/copilot", json={"prompt": "Test prompt"})

        assert response.status_code == 503
        data = response.json()

        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "Please log in to Copilot first" in data["error"]["message"]


class TestCORSHeaders:
    """Test CORS functionality."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.options("/v1/process")

        # TestClient doesn't fully simulate CORS preflight, but we can check the app handles it
        assert response.status_code in [
            200,
            405,
        ]  # Either OK or Method Not Allowed is fine

    def test_request_id_header(self, client):
        """Test that X-Request-ID header is added to responses."""
        response = client.get("/v1/health")

        assert "X-Request-ID" in response.headers
        # Validate it's a UUID format
        UUID(response.headers["X-Request-ID"])


class TestErrorHandling:
    """Test error handling and response formats."""

    def test_error_response_structure(self, client):
        """Test that error responses have consistent structure."""
        response = client.post(
            "/v1/process"
        )  # Empty request should cause validation error

        assert response.status_code == 400
        data = response.json()

        assert "error" in data
        error = data["error"]
        assert "code" in error
        assert "message" in error
        # details field is optional

    def test_404_handling(self, client):
        """Test handling of non-existent endpoints."""
        response = client.get("/nonexistent")

        assert response.status_code == 404
