# Copilot browser automator (Playwright + Chrome on Windows)

This project drives the Microsoft 365 Copilot web app in a real Chrome browser using Playwright (Python). It launches Chrome with a persistent user profile so your login session survives between runs, and it offers a tiny terminal control loop plus helper functions to interact with the page: send prompts, click buttons, upload cloud files via the picker, copy the latest Copilot reply, and download blob attachments from the last message.

Key points
- Headful Chrome (not headless) with a persistent user data dir.
- Opens: https://copilot.cloud.microsoft/
- Keeps the page open until you exit from the terminal.
- Helpers to: input into the chat box, press Send, wait for response, copy the last reply (clipboard API with PowerShell fallback), and download blob attachments.


## Project layout
- `playwright_copilot.py` – Main script that launches Chrome and exposes helper functions.
- `selectors_reference.md` – Handy selectors used in the UI (defaults are baked into the script).
- `workflow.md` / `workflow_testing.md` / `handling_copilot_page.md` – Notes and procedures for interacting with the page.
- `LICENSE` – License file for this repo.


## Requirements
- Windows 10/11
- Python 3.11+ recommended
- Google Chrome installed (stable or Dev); path is configurable in the script
- Python packages: `playwright`

Tip: Playwright also needs its driver/browsers installed once per machine. Even though this script points to your local Chrome via `executable_path`, running `playwright install` is still recommended to ensure drivers are present.


## Quick start (PowerShell)
1) Create and activate a virtual environment
2) Install dependencies (see `requirements.txt`)
3) Install Playwright drivers/browsers once (`playwright install`)
4) Run the script to launch Chrome and open Copilot

On first run, sign in to Microsoft 365 in the opened browser. Your login will persist in the configured profile directory for future runs.


## Configuration
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
- `input` – Type a prompt into a text box (you’ll be asked for the prompt and the selector; defaults are provided in the script)
- `upload` – Open the file picker (My files > copilot) and select files by name
- `click` – Click a button by selector (e.g., Send)
- `response` – Print Copilot’s latest response

Note: The helper functions behind these commands are also usable programmatically if you import this module (e.g., `copy_latest_copilot_message`, `wait_for_response_to_stabilize`, `download_blob_links_from_latest_message`, etc.).


## Helper capabilities (programmatic)
- Copy latest reply: reads via web Clipboard API with a PowerShell fallback; normalizes newlines.
- Input prompt: focuses the text box, fills your prompt, and simulates a space keypress to trigger UI listeners.
- Click button: clicks by selector; has optional logic to wait for a new response.
- Upload files: navigates the OneDrive/SharePoint picker iframe and selects files by (partial) name.
- Download attachments: finds `blob:` links in the latest message and saves them into `DOWNLOADS_DIR`.


## Troubleshooting
- “Chrome executable not found” – Update `CHROME_EXE` in `playwright_copilot.py` to your Chrome path.
- First run prompts for login – That’s expected. After login, the session persists in `USER_DATA_DIR_ENV`.
- Clipboard doesn’t capture text – The script grants site clipboard permissions and then tries Windows PowerShell `Get-Clipboard` as a fallback.
- No “Copy” button found – The code falls back to reading the message DOM text.
- Nothing downloads – Some outputs are not files; if blob links aren’t present, there’s nothing to save.
- Playwright errors about browsers – Run `playwright install` once in your environment.


## Privacy and cleanup
- The persistent profile folder is at `USER_DATA_DIR_ENV` (default: `.\.Playwright\codes`). It contains browser cookies/storage for your session.
- To log out/clear state, delete that folder (Chrome must be closed when you do this).


## License
See `LICENSE`.

