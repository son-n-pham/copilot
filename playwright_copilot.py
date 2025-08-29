"""
Open https://copilot.cloud.microsoft/?fromCode=cmcv2&redirectId=079013B7710342F5A1FDB755834168FD&auth=2 in Chrome Dev with a persistent profile.

Behavior:
- headless = False
- browser executable: C:\\Program Files\\Google\\Chrome Dev\\Application\\chrome.exe
- user data dir: %USERPROFILE%\\AppData\\Local\\Microsoft\\Playwright\\mcp-user-data
- If login is required, you can log in manually; the session will persist for next runs.
- The page stays open until you confirm shutdown in the terminal.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import re
import time

import subprocess
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, Error, Locator, Page, sync_playwright

TARGET_URL = "https://copilot.cloud.microsoft/?fromCode=cmcv2&redirectId=079013B7710342F5A1FDB755834168FD&auth=2"
# CHROME_EXE = r"C:\\Program Files\\Google\\Chrome Dev\\Application\\chrome.exe"
CHROME_EXE = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# USER_DATA_DIR_ENV = r"C:\\Users\\phamsonn\\AppData\\Local\\Microsoft\\Playwright\\codes"
USER_DATA_DIR_ENV = r".\\.Playwright\\codes"

# Default selectors from selectors_reference.md
DEFAULT_TEXT_INPUT_SELECTOR = 'role=combobox[name="Chat Input"]'
DEFAULT_SEND_BUTTON_SELECTOR = 'role=button[name="Send"]'


def expand_windows_path(path_with_env: str) -> str:
    """Expand %VARS% and normalize Windows path separators."""
    expanded = os.path.expandvars(path_with_env)
    return os.path.normpath(expanded)


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def has_existing_profile(user_data_dir: str) -> bool:
    """Heuristic: consider it existing if directory has any files/folders."""
    p = Path(user_data_dir)
    if not p.exists():
        return False
    try:
        next(p.iterdir())
        return True
    except StopIteration:
        return False


def launch_context(user_data_dir: str) -> BrowserContext:
    # Validate Chrome Dev path
    if not Path(CHROME_EXE).exists():
        print(
            "[ERROR] Chrome Dev executable not found at: " + CHROME_EXE,
            "\nPlease install Google Chrome Dev or update CHROME_EXE in this script.",
            sep="",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[INFO] Using user data dir: {user_data_dir}")
    print(f"[INFO] Using Chrome executable: {CHROME_EXE}")

    ctx: BrowserContext
    with sync_playwright() as p:
        # launch_persistent_context returns a Context that stays alive while this process runs.
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=CHROME_EXE,
            args=[
                "--disable-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        # Ensure we have at least one page
        page: Page
        if ctx.pages:
            page = ctx.pages[0]
        else:
            page = ctx.new_page()

        print(f"[INFO] Navigating to {TARGET_URL} ...")
        try:
            page.goto(TARGET_URL, wait_until="load", timeout=90_000)
        except Error as e:
            print(f"[WARN] Navigation issue: {e}")

        # Guidance for manual login persistence
        if has_existing_profile(user_data_dir):
            print(
                "[INFO] Found existing profile; if you were previously logged in, it should auto-sign you in."
            )
        else:
            print(
                "[INFO] First run with a new profile. If the site prompts for login, please sign in manually."
            )

        print("\n--- Control ---")
        print(
            "This window will stay open for further work.\n\n"
            "Commands:\n"
            "  exit | quit | q      - Close the browser\n"
            "  help | h | ?         - Show this help\n"
            "  refresh              - Reload current page\n"
            "  goto <url>           - Navigate to a URL\n"
            "  where                - Show current URL\n"
            "  input                - Type a prompt into a text box\n"
            "     - You will be asked for:\n"
            "       • Prompt text\n"
            '       • Selector of the text box (e.g., role=combobox[name="Chat Input"]) \n'
            "  upload               - Attach cloud files via picker (My files > copilot)\n"
            "     - Enter comma-separated file names to select (e.g., report.pdf, data.csv)\n"
            '  click                - Click a button by selector (e.g., role=button[name="Send"]) \n'
            "  response             - Retrieve and print Copilot's latest response\n\n"
            "When you're done, type 'exit' (or press Ctrl+C) to close the browser."
        )

        try:
            # Simple REPL to keep process alive and allow future extension.
            while True:
                cmd = input("command> ").strip().lower()
                if cmd in {"exit", "quit", "q"}:
                    break
                elif cmd in {"help", "h", "?"}:
                    print(
                        "\nCommands:\n"
                        "  exit | quit | q      - Close the browser\n"
                        "  help | h | ?         - Show this help\n"
                        "  refresh              - Reload current page\n"
                        "  goto <url>           - Navigate to a URL\n"
                        "  where                - Show current URL\n"
                        "  input                - Type a prompt into a text box\n"
                        "     - You will be asked for:\n"
                        "       • Prompt text\n"
                        '       • Selector of the text box (e.g., role=combobox[name="Chat Input"]) \n'
                        "  upload               - Attach cloud files via picker (My files > copilot)\n"
                        "     - Enter comma-separated file names to select (e.g., report.pdf, data.csv)\n"
                        '  click                - Click a button by selector (e.g., role=button[name="Send"]) \n'
                        "  response             - Retrieve and print Copilot's latest response\n"
                    )
                elif cmd == "response":
                    try:
                        print("[INFO] Retrieving latest Copilot response (copy)…")
                        copied = None
                        max_attempts = 3
                        for attempt in range(1, max_attempts + 1):
                            copied = copy_latest_copilot_message(page)
                            if copied:
                                break
                            print(
                                f"[INFO] Copy button not ready, attempt {attempt}/{max_attempts}. Waiting..."
                            )
                            try:
                                page.wait_for_function(
                                    """() => {
                                        const ms = document.querySelectorAll('[data-testid="copilot-message-div"]');
                                        if (!ms.length) return false;
                                        const last = ms[ms.length - 1];
                                        return !!(
                                            last.querySelector('[data-testid="CopyButtonTestID"]') ||
                                            last.querySelector('[data-testid="CopyButtonTestId"]') ||
                                            last.querySelector('button[aria-label="Copy"]')
                                        );
                                    }""",
                                    timeout=5000,
                                )
                            except Error:
                                pass
                            page.wait_for_timeout(1500)

                        if copied is None:
                            # Fallback to DOM extraction if copy failed after retries
                            copied = retrieve_latest_response(page)
                        print("\n----- COPILOT RESPONSE -----")
                        print(copied)
                        print("----- END RESPONSE -----\n")
                    except Exception as e:
                        print(f"[ERROR] Failed to retrieve response: {e}")
                elif cmd == "refresh":
                    try:
                        page.reload(wait_until="load")
                        print("[INFO] Page reloaded.")
                    except Error as e:
                        print(f"[WARN] Reload failed: {e}")
                elif cmd.startswith("goto "):
                    url = cmd.split(" ", 1)[1]
                    try:
                        page.goto(url, wait_until="load")
                        print(f"[INFO] Navigated to {url}")
                    except Error as e:
                        print(f"[WARN] Navigation failed: {e}")
                elif cmd == "where":
                    try:
                        print(f"[INFO] Current URL: {page.url}")
                    except Exception:
                        print("[INFO] Current URL: <unknown>")
                elif cmd == "input":
                    prompt_text = input("Enter text prompt: ").strip()
                    selector = input(
                        f"Enter selector for text box [default: {DEFAULT_TEXT_INPUT_SELECTOR}]: "
                    ).strip()
                    if not selector:
                        selector = DEFAULT_TEXT_INPUT_SELECTOR
                    if prompt_text and selector:
                        input_prompt_into_text_box(page, prompt_text, selector)
                    else:
                        print("[WARN] Both prompt and selector are required.")
                elif cmd == "upload":
                    file_names_input = input(
                        "Enter file names (comma-separated): "
                    ).strip()
                    if file_names_input:
                        file_list = [
                            name.strip() for name in file_names_input.split(",")
                        ]
                        upload_files_from_copilot_folder(page, file_list)
                    else:
                        print("[WARN] File names are required.")
                elif cmd == "click":
                    selector = input(
                        f"Enter selector for button [default: {DEFAULT_SEND_BUTTON_SELECTOR}]: "
                    ).strip()
                    if not selector:
                        selector = DEFAULT_SEND_BUTTON_SELECTOR
                    if selector:
                        click_button(page, selector)
                    else:
                        print("[WARN] Button selector is required.")
                else:
                    if cmd:
                        print("Unknown command. Type 'help' for options.")
        except KeyboardInterrupt:
            print("\n[INFO] Ctrl+C received. Shutting down...")
        finally:
            print("[INFO] Closing browser context...")
            try:
                ctx.close()
            except Exception:
                pass

        # Exiting the Playwright context closes the underlying driver.
        return ctx


TESTID_CHAT_QUESTION = "chatQuestion"
TESTID_COPILOT_MESSAGE = "copilot-message-div"
TESTID_COPY_BUTTON = (
    "CopyButtonTestID"  # Historical default; real DOM may use "CopyButtonTestId"
)


def _chat_questions(page: Page) -> Locator:
    return page.get_by_test_id(TESTID_CHAT_QUESTION)


def _copilot_messages(page: Page) -> Locator:
    return page.get_by_test_id(TESTID_COPILOT_MESSAGE)


def _copy_button_in_message(message_locator: Locator) -> Locator:
    """
    Return a robust locator for the Copy action on a Copilot message.
    Covers multiple test-id variants and aria-label fallback.
    """
    return message_locator.locator(
        "[data-testid='CopyButtonTestId'], [data-testid='CopyButtonTestID'], button[aria-label='Copy'], [aria-label='Copy'][role='button']"
    )


# Count all chat questions; also return the locator
def count_return_chat_questions(page: Page) -> tuple[int, Locator]:
    loc = _chat_questions(page)
    return loc.count(), loc


# Count all copilot messages; also return the locator
def count_return_copilot_messages(page: Page) -> tuple[int, Locator]:
    loc = _copilot_messages(page)
    return loc.count(), loc


def is_latest_copilot_message_fully_generated(page: Page) -> bool:
    chat_count, _ = count_return_chat_questions(page)
    msg_count, msgs = count_return_copilot_messages(page)

    if chat_count < 1 or msg_count != chat_count:
        return False

    last_msg = msgs.nth(msg_count - 1)  # nth() is a method → ()
    return _copy_button_in_message(last_msg).count() > 0


def wait_for_latest_copilot_message_fully_generated(
    page: Page, timeout: int = 120
) -> bool:
    """Best-effort wait: return when at least one Copilot message is visible.

    Uses locators so it works even if content is in a frame. Full generation
    (copy button presence) is not required here; copy logic has its own fallbacks.
    """
    end = time.time() + timeout
    while time.time() < end:
        try:
            msg_count, msgs = count_return_copilot_messages(page)
            if msg_count > 0:
                last_msg = msgs.nth(msg_count - 1)
                try:
                    if last_msg.is_visible():
                        print("[INFO] Latest copilot message is visible.")
                        return True
                except Error:
                    pass
        except Error:
            pass
        page.wait_for_timeout(200)
    return False


# ...existing code...
# ...existing code...
def _read_clipboard_quick(page: Page) -> str | None:
    """Quick clipboard reading with single attempt."""
    # Try web clipboard API first
    try:
        parsed = urlparse(page.url)
        origin = (
            f"{parsed.scheme}://{parsed.netloc}"
            if parsed.scheme and parsed.netloc
            else None
        )
        if origin:
            page.context.grant_permissions(
                ["clipboard-read", "clipboard-write"], origin=origin
            )
        return page.evaluate("async () => await navigator.clipboard.readText()")
    except Exception:
        pass

    # Try PowerShell fallback on Windows
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
            capture_output=True,
            text=True,
            timeout=2,  # Quick timeout
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass

    return None


def copy_latest_copilot_message_quick(page: Page) -> str | None:
    """
    Quick version of copy_latest_copilot_message with shorter timeouts.
    Returns None if copy button isn't available quickly.
    """
    msg_count, msgs = count_return_copilot_messages(page)
    if msg_count < 1:
        print("[DEBUG] No Copilot messages found on page")
        return None

    last_msg = msgs.nth(msg_count - 1)
    try:
        last_msg.scroll_into_view_if_needed(timeout=2000)
    except Error:
        pass

    copy_btn = _copy_button_in_message(last_msg)

    # Try clicking the copy button with short timeout
    try:
        copy_btn.first.wait_for(
            state="visible", timeout=3_000
        )  # Reduced from 10s to 3s
        copy_btn.first.click(timeout=3_000)
        print("[INFO] Copy button clicked (quick).")

        # Give the page time to write to the clipboard
        page.wait_for_timeout(500)  # Reduced from 800ms to 500ms

        # Try to read clipboard quickly
        clipboard_text = _read_clipboard_quick(page)
        if clipboard_text:
            return clipboard_text.replace("\r\n", "\n").rstrip("\n\r\0")

    except Error as e:
        print(f"[DEBUG] Quick copy button click failed: {e}")

    return None


def copy_latest_copilot_message(page: Page) -> str | None:
    # Try a short wait, but proceed best-effort if not visible yet
    if not wait_for_latest_copilot_message_fully_generated(page, timeout=15):
        print(
            "[WARN] Latest copilot message is not fully generated; proceeding best-effort."
        )
        chat_count, _ = count_return_chat_questions(page)
        msg_count, _ = count_return_copilot_messages(page)
        print(f"[DEBUG] Chat questions found: {chat_count}")
        print(f"[DEBUG] Copilot messages found: {msg_count}")

    msg_count, msgs = count_return_copilot_messages(page)
    if msg_count < 1:
        print("[DEBUG] No Copilot messages found on page")
        return None

    last_msg = msgs.nth(msg_count - 1)
    try:
        last_msg.scroll_into_view_if_needed(timeout=5000)
    except Error:
        pass

    copy_btn = _copy_button_in_message(last_msg)

    # Try clicking the copy button
    copy_success = False
    try:
        copy_btn.first.wait_for(state="visible", timeout=10_000)
        copy_btn.first.click(timeout=10_000)
        copy_success = True
        print("[INFO] Copy button clicked.")
    except Error as e:
        print(f"[ERROR] Failed to click copy button: {e}")

    if not copy_success:
        # If we can't click the copy button, return the DOM text as a fallback.
        try:
            dom_text = last_msg.inner_text()
            print("[DEBUG] Returning DOM text due to copy click failure.")
            return dom_text
        except Error as e:
            print(f"[ERROR] Failed to read message text: {e}")
            return None

    # Give the page time to write to the clipboard
    page.wait_for_timeout(800)

    # Prefer web clipboard API; grant permissions and read
    def _read_clipboard_via_web() -> str | None:
        try:
            parsed = urlparse(page.url)
            origin = (
                f"{parsed.scheme}://{parsed.netloc}"
                if parsed.scheme and parsed.netloc
                else None
            )
            if origin:
                # Grant both read and write just in case the site’s handler needs it
                page.context.grant_permissions(
                    ["clipboard-read", "clipboard-write"], origin=origin
                )

            # Playwright will await a returned Promise automatically
            return page.evaluate("async () => await navigator.clipboard.readText()")
        except Exception as e:
            print(f"[DEBUG] navigator.clipboard.readText() failed: {e}")
            return None

    # PowerShell fallback on Windows
    def _read_clipboard_via_powershell() -> str | None:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout
            else:
                print(
                    f"[DEBUG] PowerShell Get-Clipboard failed: {result.stderr.strip()}"
                )
        except Exception as e:
            print(f"[DEBUG] PowerShell clipboard read failed: {e}")
        return None

    # Try a few times to give the clipboard time to update
    clipboard_text: str | None = None
    for attempt in range(3):
        clipboard_text = _read_clipboard_via_web()
        if clipboard_text:
            break
        if not clipboard_text:
            clipboard_text = _read_clipboard_via_powershell()
        if clipboard_text:
            break
        page.wait_for_timeout(400)

    if clipboard_text:
        # Normalize output a bit
        text = clipboard_text.replace("\r\n", "\n").rstrip("\n\r\0")
        print(f"[DEBUG] Clipboard text length: {len(text)}")
        return text

    # Final fallback: read from DOM
    try:
        dom_text = last_msg.inner_text()
        print("[DEBUG] Clipboard empty; returning DOM text.")
        return dom_text
    except Error as e:
        print(f"[ERROR] Failed to read message text: {e}")
        return None


def input_prompt_into_text_box(page: Page, prompt: str, selector: str) -> None:
    """Helper to input text into a page element."""
    print(f"[DEBUG] Inputting prompt into selector '{selector}'")
    try:
        page.fill(selector, prompt)
        print(f"[INFO] Successfully inputted text into '{selector}'")
    except Error as e:
        print(f"[ERROR] Failed to input text: {e}")


def upload_files_from_copilot_folder(page: Page, file_list: list[str]) -> None:
    """Attach cloud files via the Microsoft 365 Copilot file picker (Steps 4–6).

    Implements:
      - Step 4: Open "Add content and agents" > "Attach cloud files".
      - Step 5: Enter File Picker iframe, click "My files", then open the "copilot" folder.
      - Step 6: Select all files whose names are provided in file_list, then click "Select".

    Notes:
      - Uses role-based selectors for reliability.
      - Uses regex for partial name matching of file checkboxes.
    """

    # Step 4: Access file upload interface
    try:
        print("[INFO] Opening 'Add content and agents' menu…")
        page.get_by_role("button", name="Add content and agents").click()
    except Error as e:
        print(f"[ERROR] Couldn't open 'Add content and agents': {e}")
        return

    try:
        print("[INFO] Choosing 'Attach cloud files'…")
        page.get_by_role("button", name="Attach cloud files").click()
    except Error as e:
        print(f"[ERROR] Couldn't click 'Attach cloud files': {e}")
        return

    # Step 5: Navigate SharePoint/OneDrive file picker (iframe)
    try:
        print("[INFO] Waiting for File Picker iframe…")
        iframe_el = page.wait_for_selector(
            'iframe[title="File Picker"]', state="visible", timeout=30000
        )
        frame = iframe_el.content_frame() if iframe_el else None
        if frame is None:
            print(
                "[ERROR] File Picker iframe frame not available (content_frame() returned None)."
            )
            return

        # Click "My files" if present (some contexts default here already)
        try:
            my_files_btn = frame.get_by_role("button", name="My files")
            if my_files_btn.is_visible():
                my_files_btn.click()
                print("[INFO] Clicked 'My files'.")
        except Error:
            # Best-effort: continue if not present
            print("[DEBUG] 'My files' button not visible; proceeding.")

        # Enter the target folder 'copilot' with exact match
        try:
            frame.get_by_role("link", name=re.compile(r"^copilot$", re.I)).click()
            print("[INFO] Entered 'copilot' folder.")
        except Error as e:
            print(f"[ERROR] Couldn't enter 'copilot' folder: {e}")
            return
    except Error as e:
        print(f"[ERROR] File Picker not available: {e}")
        return

    # Step 6: Select target files and confirm
    any_selected = False
    for file_name in file_list:
        # Use partial name matching (case-insensitive)
        pattern = re.compile(re.escape(file_name), re.I)
        try:
            checkbox = frame.get_by_role("checkbox", name=pattern)
            checkbox.click()
            print(f"[INFO] Selected file checkbox matching: '{file_name}'.")
            any_selected = True
        except Error as e:
            print(f"[WARN] Could not select file '{file_name}': {e}")

    if not any_selected:
        print("[ERROR] No files were selected; aborting before clicking 'Select'.")
        return

    try:
        frame.get_by_role("button", name=re.compile(r"^Select$", re.I)).click()
        print("[INFO] Confirmed selection by clicking 'Select'.")
    except Error as e:
        print(f"[ERROR] Failed to confirm selection: {e}")


def click_button(page: Page, selector: str) -> None:
    """Helper to click a button identified by the selector."""
    print(f"[DEBUG] Clicking button with selector '{selector}'")
    try:
        # Get message count before the action that triggers a response
        pre_response_msg_count, _ = count_return_copilot_messages(page)

        page.click(selector)
        print(f"[INFO] Successfully clicked button '{selector}'")

        # Check if the clicked button is the Send button
        if selector == DEFAULT_SEND_BUTTON_SELECTOR or "send" in selector.lower():
            print("[INFO] Send button detected, retrieving Copilot response…")
            try:
                # Prefer authoritative signal: wait for Copy button on the last message
                if wait_for_copy_button_on_last_message(
                    page, pre_response_msg_count, timeout_s=45
                ):
                    print(
                        "[INFO] Copy button detected on latest message — response complete."
                    )
                else:
                    print(
                        "[INFO] Copy button not detected; falling back to stability wait."
                    )
                    # Fall back to content stability, ignoring known in-progress markers
                    wait_for_response_to_stabilize(
                        page,
                        pre_response_msg_count,
                        timeout_s=60,
                        stability_period_s=3.0,
                    )

                response_text = retrieve_latest_response(page)

                print("\n----- COPILOT RESPONSE -----")
                print(response_text or "No response retrieved")
                print("----- END RESPONSE -----\n")
            except Exception as e:
                print(f"[ERROR] Failed to retrieve response: {e}")
    except Error as e:
        print(f"[ERROR] Failed to click button: {e}")


def wait_for_copy_button_on_last_message(
    page: Page,
    pre_response_msg_count: int,
    timeout_s: int = 45,
) -> bool:
    """
    Waits for a new Copilot message to appear and for its Copy button to become visible.
    Returns True if the Copy button is seen on the last message within timeout.
    """
    deadline = time.time() + timeout_s

    # First, wait for a new message container to show up.
    try:
        page.wait_for_function(
            """(pre) => {
                const ms = document.querySelectorAll('[data-testid="copilot-message-div"]');
                return ms.length > pre;
            }""",
            arg=pre_response_msg_count,
            timeout=min(15_000, int(timeout_s * 1000)),
        )
    except Error:
        curr, _ = count_return_copilot_messages(page)
        if curr <= pre_response_msg_count:
            return False

    # Then, wait for the copy button on the new last message.
    while time.time() < deadline:
        try:
            _, msgs = count_return_copilot_messages(page)
            last_msg = msgs.last
            try:
                last_msg.scroll_into_view_if_needed(timeout=1000)
            except Error:
                pass
            copy_btn = _copy_button_in_message(last_msg).first
            copy_btn.wait_for(state="visible", timeout=1000)
            return True
        except Error:
            page.wait_for_timeout(300)

    return False


def wait_for_response_to_stabilize(
    page: Page,
    pre_response_msg_count: int,
    timeout_s: int = 60,
    stability_period_s: float = 2.0,
) -> bool:
    """
    Waits for a new Copilot message to appear and then for its content to stabilize.

    Args:
        page (Page): The Playwright page object.
        pre_response_msg_count (int): The number of Copilot messages before the action.
        timeout_s (int): Total time to wait for stabilization.
        stability_period_s (float): How long the content must remain unchanged.

    Returns:
        bool: True if the response stabilized, False if it timed out.
    """
    print("[INFO] Waiting for response to appear and stabilize...")

    # Wait for a new message to appear
    try:
        page.wait_for_function(
            f"document.querySelectorAll('[data-testid=\"copilot-message-div\"]').length > {pre_response_msg_count}",
            timeout=15000,
        )
        print("[DEBUG] New response message container appeared.")
    except Error:
        current_count, _ = count_return_copilot_messages(page)
        if current_count <= pre_response_msg_count:
            print("[ERROR] No new response message appeared within timeout.")
            return False

    # Known in-progress phrases that should not count as "stable"
    in_progress_markers = (
        "Generating response",
        "Searching",
        "Searching the web",
        "Working on it",
        "Analyzing",
        "Browsing",
        "Researching",
        "Looking for",
    )

    last_text = ""
    last_change_time = time.time()
    end_time = time.time() + timeout_s

    while time.time() < end_time:
        try:
            _, msgs = count_return_copilot_messages(page)
            last_msg = msgs.last
            current_text = last_msg.inner_text()
        except Error:
            last_msg = None
            current_text = ""

        # Primary completion signal: Copy button appears on the last message
        try:
            if last_msg is not None and _copy_button_in_message(last_msg).count() > 0:
                print(
                    "[INFO] Copy button detected on latest message — response complete."
                )
                return True
        except Error:
            # Ignore and rely on stability fallback
            pass

        # Fallback: textual stability for a short period
        if current_text != last_text:
            last_text = current_text
            last_change_time = time.time()

        # Only consider stable if it's not stuck on an in-progress marker
        has_in_progress_marker = any(m in last_text for m in in_progress_markers)

        if (
            time.time() - last_change_time
        ) > stability_period_s and not has_in_progress_marker:
            print("[INFO] Response content has been stable.")
            return True

        time.sleep(0.5)  # Poll every 500ms

    print("[WARN] Timed out waiting for response to stabilize.")
    return False


def retrieve_latest_response(page: Page) -> str:
    """
    Retrieves the latest response content from Copilot. Assumes response is complete.
    """
    try:
        print("[INFO] Extracting Copilot response content...")
        msg_count, msgs = count_return_copilot_messages(page)
        if msg_count < 1:
            return "No Copilot messages found on page"

        response_text = msgs.last.inner_text()
        print("[INFO] Successfully extracted Copilot response")
        return response_text.strip()

    except Error as e:
        print(f"[ERROR] Failed to extract Copilot response: {e}")
        return "[Error: Could not extract response]"


def main() -> None:
    user_data_dir = expand_windows_path(USER_DATA_DIR_ENV)
    ensure_dir(user_data_dir)

    # Log whether we expect an existing login session
    if has_existing_profile(user_data_dir):
        print(
            "[INFO] Detected existing profile data; attempting to reuse saved login state."
        )
    else:
        print("[INFO] No existing profile data found; a fresh profile will be created.")

    launch_context(user_data_dir)


if __name__ == "__main__":
    main()
