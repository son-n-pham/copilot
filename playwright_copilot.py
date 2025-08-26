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

from playwright.sync_api import BrowserContext, Error, Page, sync_playwright


TARGET_URL = "https://copilot.cloud.microsoft/?fromCode=cmcv2&redirectId=079013B7710342F5A1FDB755834168FD&auth=2"
# CHROME_EXE = r"C:\\Program Files\\Google\\Chrome Dev\\Application\\chrome.exe"
CHROME_EXE = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
USER_DATA_DIR_ENV = r"C:\\Users\\phamsonn\\AppData\\Local\\Microsoft\\Playwright\\codes"


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
            '  click                - Click a button by selector (e.g., role=button[name="Send"]) \n\n'
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
                    )
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
                    selector = input("Enter selector for text box: ").strip()
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
                    selector = input("Enter selector for button: ").strip()
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
        page.click(selector)
        print(f"[INFO] Successfully clicked button '{selector}'")
    except Error as e:
        print(f"[ERROR] Failed to click button: {e}")


def retrieve_response(page: Page, selector: str) -> str:
    """Helper to retrieve text from a page element identified by the selector."""
    print(f"[DEBUG] Retrieving response from selector '{selector}'")
    try:
        element = page.query_selector(selector)
        if element:
            text = element.text_content() or ""
            print(
                f"[INFO] Retrieved text: {text[:100]}{'...' if len(text) > 100 else ''}"
            )
            return text
        else:
            print(f"[WARN] Element not found with selector '{selector}'")
            return ""
    except Error as e:
        print(f"[ERROR] Failed to retrieve response: {e}")
        return ""


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
