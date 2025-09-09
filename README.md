# Copilot browser automator (Playwright + Chrome on Windows)

This project drives the Microsoft 365 Copilot web app in a real Chrome browser using Playwright (Python). It launches Chrome with a persistent user profile so your login session survives between runs, and it offers a tiny terminal control loop plus helper functions to interact with the page: send prompts, click buttons, upload cloud files via the picker, copy the latest Copilot reply, and download blob attachments from the last message.

**NEW: FastAPI REST API** - This project now includes a production-ready REST API for processing text prompts and file attachments with comprehensive validation and error handling.

Key points
- Headful Chrome (not headless) with a persistent user data dir.
- Opens: https://copilot.cloud.microsoft/
- Keeps the page open until you exit from the terminal.
- Helpers to: input into the chat box, press Send, wait for response, copy the last reply (clipboard API with PowerShell fallback), and download blob attachments.
- **FastAPI REST API** for programmatic access to text and file processing capabilities.


## Project layout
- `playwright_copilot.py` – Main script that launches Chrome and exposes helper functions.
- `app/` – FastAPI REST API application
  - `main.py` – FastAPI app with middleware and routing
  - `config.py` – Configuration management with environment variables
  - `schemas.py` – Pydantic models for request/response validation
  - `models.py` – Internal data models and enums
  - `routers/process.py` – API endpoints for processing and health checks
  - `services/processor.py` – Core validation and processing logic
  - `utils/hash.py` – Streaming SHA256 computation utilities
- `tests/` – Comprehensive test suite with pytest
- `selectors_reference.md` – Handy selectors used in the UI (defaults are baked into the script).
- `workflow.md` / `workflow_testing.md` / `handling_copilot_page.md` – Notes and procedures for interacting with the page.
- `LICENSE` – License file for this repo.


## Requirements
- Windows 10/11
- Python 3.10+ recommended (3.11+ for Playwright features)
- Google Chrome installed (stable or Dev); path is configurable in the script
- Python packages: see `requirements.txt`

Tip: Playwright also needs its driver/browsers installed once per machine. Even though this script points to your local Chrome via `executable_path`, running `playwright install` is still recommended to ensure drivers are present.


## Quick start (PowerShell)

### Setup Virtual Environment
```powershell
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright drivers (one-time setup)
playwright install
```

### Run Playwright Browser Automation
```powershell
# Run the script to launch Chrome and open Copilot
python playwright_copilot.py
```

On first run, sign in to Microsoft 365 in the opened browser. Your login will persist in the configured profile directory for future runs.

### Run FastAPI REST API
```powershell
# Start the API server
uvicorn app.main:app --reload --port 8000

# Or run directly with Python
python -m app.main
```

The API will be available at:
- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/v1/health


## FastAPI REST API Documentation

### Overview
The REST API provides a stateless service for processing text prompts and file attachments with comprehensive validation, error handling, and structured responses.

### API Endpoints

#### POST /v1/process
Process text prompts and/or file uploads (echo/metadata service).

**Request Format:**
```
Content-Type: multipart/form-data

Fields:
- prompt: string (optional) - Text input to process
- files: File[] (optional) - File uploads (0-3 files, max 10MB each)
```

**Validation Rules:**
- At least one of `prompt` or `files` must be provided
- Maximum 3 files per request
- Maximum 10MB per file
- Supported MIME types: `text/plain`, `application/pdf`, `image/png`, `image/jpeg`
- Server-side MIME type detection for security

**Success Response (200):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "prompt": "Analyze this document",
  "files": [
    {
      "filename": "report.pdf",
      "content_type": "application/pdf",
      "size_bytes": 1024000,
      "sha256": "abc123def456..."
    }
  ],
  "result": {
    "message": "Processed 1 file and text prompt successfully"
  },
  "meta": {
    "received_at": "2025-01-08T03:15:00.000Z",
    "duration_ms": 125,
    "warnings": []
  }
}
```

**Error Responses:**
- **400 Bad Request**: Validation errors (missing input, too many files, file too large)
- **415 Unsupported Media Type**: Invalid file type
- **422 Unprocessable Entity**: Malformed request data
- **500 Internal Server Error**: Unexpected server errors

#### POST /v1/process/copilot
Process text prompts using real Microsoft 365 Copilot via Playwright automation.

**Prerequisites:**
- Chrome browser installed at configured path
- **IMPORTANT**: You must be logged into Microsoft 365 Copilot manually in Chrome first
- Supports text prompts with optional file uploads from Copilot SharePoint folder

**Initial Setup (Required):**
1. Run `python playwright_copilot.py` from the terminal
2. When Chrome opens, complete the Microsoft 365 login process manually
3. Your login session will be saved in the persistent profile (`.\.Playwright\codes`)
4. Close the browser and terminal
5. The API will now work for future `/v1/process/copilot` requests

**Note**: If you get a 503 error mentioning login requirements, repeat the setup steps above.

**Request Format:**
```
Content-Type: application/json

Fields:
- prompt: string (required) - Text input to send to Copilot
- files_to_upload: string[] (optional) - List of file names to upload from Copilot SharePoint folder
```

**Success Response (200):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "prompt": "Analyze these files",
  "files": [],
  "result": {
    "message": "Based on the uploaded files..."
  },
  "meta": {
    "received_at": "2025-01-08T03:15:00.000Z",
    "duration_ms": 45000,
    "warnings": []
  }
}
```

**Error Responses:**
- **400 Bad Request**: Missing or empty prompt
- **500 Internal Server Error**: Browser/Chrome issues, automation failures
- **503 Service Unavailable**: Login required or Copilot service unavailable

**Note:** Response times are typically 30-120 seconds as this endpoint launches Chrome, navigates to Copilot, sends the prompt, waits for the response, and extracts the reply.

#### GET /v1/health
Health check endpoint for monitoring and load balancing.

**Response (200):**
```json
{
  "status": "ok"
}
```

### Example API Usage

#### Curl Examples
```bash
# Process text prompt only (echo service)
curl -X POST "http://localhost:8000/v1/process" \
  -F "prompt=Analyze this text"

# Process file only (echo service)
curl -X POST "http://localhost:8000/v1/process" \
  -F "files=@document.pdf"

# Process both prompt and files (echo service)
curl -X POST "http://localhost:8000/v1/process" \
  -F "prompt=Analyze these documents" \
  -F "files=@test.pdf" \
  -F "files=@data.txt"

# Process with real Microsoft 365 Copilot (text only)
curl -X POST "http://localhost:8000/v1/process/copilot" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'

# Process with real Microsoft 365 Copilot (with file uploads)
curl -X POST "http://localhost:8000/v1/process/copilot" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze these files", "files_to_upload": ["report.pdf", "data.txt"]}'

# Health check
curl -X GET "http://localhost:8000/v1/health"
```

#### Python Examples
```python
import httpx

# Process with echo service (files + prompt)
with open("document.pdf", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/v1/process",
        data={"prompt": "Analyze this document"},
        files={"files": ("document.pdf", f, "application/pdf")}
    )
    result = response.json()
    print(f"Echo result: {result['result']['message']}")

# Process with real Microsoft 365 Copilot (text only)
async def query_copilot():
    async with httpx.AsyncClient(timeout=180.0) as client:  # Extended timeout
        response = await client.post(
            "http://localhost:8000/v1/process/copilot",
            json={"prompt": "Explain quantum computing in simple terms"}
        )
        result = response.json()
        print(f"Copilot says: {result['result']['message']}")

# Process with real Microsoft 365 Copilot (with file uploads)
async def query_copilot_with_files():
    async with httpx.AsyncClient(timeout=180.0) as client:  # Extended timeout
        response = await client.post(
            "http://localhost:8000/v1/process/copilot",
            json={
                "prompt": "Analyze these files", 
                "files_to_upload": ["report.pdf", "data.txt"]
            }
        )
        result = response.json()
        print(f"Copilot says: {result['result']['message']}")

# Run the async example
# asyncio.run(query_copilot())
```

### Environment Configuration

The API can be configured via environment variables or a `.env` file:

```bash
# File upload limits
MAX_FILE_SIZE_MB=10
MAX_FILES=3

# Allowed MIME types (comma-separated)
ALLOWED_MIME_TYPES=text/plain,application/pdf,image/png,image/jpeg

# CORS origins (comma-separated)
FASTAPI_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Logging level
LOG_LEVEL=INFO

# API metadata
API_TITLE=Copilot REST API
API_DESCRIPTION=FastAPI REST API for processing text prompts and file attachments
API_VERSION=1.0.0

# Copilot integration settings
COPILOT_URL=https://copilot.cloud.microsoft/?fromCode=cmcv2&redirectId=079013B7710342F5A1FDB755834168FD&auth=2
CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe
USER_DATA_DIR=.\.Playwright\codes
DOWNLOADS_DIR=.\.Playwright\downloads
COPILOT_TIMEOUT=120
```

### Development and Testing

#### Running Tests
```powershell
# Run all tests
pytest

# Run with coverage report
pytest --cov=app tests/

# Run specific test file
pytest tests/test_process.py

# Run with verbose output
pytest -v
```

#### VS Code Integration
1. **Test Explorer**: Install the Python Test Explorer extension to run tests directly in VS Code
2. **Integrated Terminal**: Use Ctrl+` to open the integrated terminal
3. **Debug Configuration**: Set breakpoints and debug tests with F5

#### Test Coverage
The test suite includes:
- ✅ Happy path scenarios (prompt only, files only, both)
- ✅ Validation error cases (empty request, too many files, file too large)
- ✅ Security validation (unsupported MIME types, malformed data)
- ✅ Edge cases (empty files, same filenames, whitespace-only prompts)
- ✅ Response schema validation
- ✅ Health endpoint functionality
- ✅ Error handling and CORS headers

### Security Features
- **File size limits** enforced before processing
- **MIME type validation** using server-side content detection
- **Input sanitization** for all form fields
- **Request ID tracking** for audit trails
- **Structured error responses** without sensitive information leakage
- **CORS configuration** for cross-origin access control

### Performance Characteristics
- **Stateless design** - no persistent file storage
- **Streaming file processing** - efficient memory usage for large files
- **SHA256 computation** - streaming hash calculation to avoid memory spikes
- **Request/response logging** - comprehensive monitoring capabilities


## Playwright Browser Automation Configuration

Defaults are defined at the top of `playwright_copilot.py`:
- TARGET_URL – Copilot web app URL
- CHROME_EXE – Path to Chrome. Update this if your Chrome is in a different location.
- USER_DATA_DIR_ENV – Persistent profile folder (relative to repo by default). This is where your session is stored.
- DOWNLOADS_DIR – Where downloaded files are saved.

Selectors the script uses by default (from `selectors_reference.md`):
- Text input: `role=combobox[name="Chat Input"]`
- Send button: `role=button[name="Send"]`


## What the script does at runtime
1) Ensures the user data and downloads directories exist.
2) Launches Chrome with a persistent context at `USER_DATA_DIR_ENV`.
3) Navigates to the Copilot URL.
4) Leaves the page open and prints a small set of terminal commands you can invoke.

Terminal controls (intended interface)
- `exit`, `quit`, `q` – Close the browser
- `help`, `h`, `?` – Show help
- `refresh` – Reload current page
- `goto <url>` – Navigate to a URL
- `where` – Print current URL
- `input` – Type a prompt into a text box (you'll be asked for the prompt and the selector; defaults are provided in the script)
- `upload` – Open the file picker (My files > copilot) and select files by name
- `click` – Click a button by selector (e.g., Send)
- `response` – Print Copilot's latest response

Note: The helper functions behind these commands are also usable programmatically if you import this module (e.g., `copy_latest_copilot_message`, `wait_for_response_to_stabilize`, `download_blob_links_from_latest_message`, etc.).


## Helper capabilities (programmatic)
- Copy latest reply: reads via web Clipboard API with a PowerShell fallback; normalizes newlines.
- Input prompt: focuses the text box, fills your prompt, and simulates a space keypress to trigger UI listeners.
- Click button: clicks by selector; has optional logic to wait for a new response.
- Upload files: navigates the OneDrive/SharePoint picker iframe and selects files by (partial) name.
- Download attachments: finds `blob:` links in the latest message and saves them into `DOWNLOADS_DIR`.


## Troubleshooting

### FastAPI API Issues
- **"Module not found" errors**: Ensure virtual environment is activated and dependencies installed
- **CORS errors**: Configure `FASTAPI_CORS_ORIGINS` environment variable with your frontend URL
- **File upload failures**: Check file size limits and MIME type restrictions
- **Test failures**: Run `pytest -v` for detailed test output and ensure all dependencies are installed

### Copilot Integration Issues
- **503 Service Unavailable**: Authentication required. Run `python playwright_copilot.py`, log in manually, then try the API again
- **500 Internal Server Error with "login" or "disabled" messages**: Same as above - manual login required
- **Chrome not opening**: Update `CHROME_EXE` in configuration or install Chrome
- **Timeout errors**: Copilot may be slow or unavailable; try again later
- **Send button disabled**: Indicates authentication issues - complete manual login setup

### Playwright Browser Issues
- "Chrome executable not found" – Update `CHROME_EXE` in `playwright_copilot.py` to your Chrome path.
- First run prompts for login – That's expected. After login, the session persists in `USER_DATA_DIR_ENV`.
- Clipboard doesn't capture text – The script grants site clipboard permissions and then tries Windows PowerShell `Get-Clipboard` as a fallback.
- No "Copy" button found – The code falls back to reading the message DOM text.
- Nothing downloads – Some outputs are not files; if blob links aren't present, there's nothing to save.
- Playwright errors about browsers – Run `playwright install` once in your environment.


## Privacy and cleanup
- The persistent profile folder is at `USER_DATA_DIR_ENV` (default: `.\.Playwright\codes`). It contains browser cookies/storage for your session.
- To log out/clear state, delete that folder (Chrome must be closed when you do this).
- The FastAPI service is stateless and does not persist uploaded files.


## License
See `LICENSE`.
