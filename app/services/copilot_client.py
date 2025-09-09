"""Copilot client service using Playwright to interact with Microsoft 365 Copilot."""

import os
import sys
import time
import asyncio
import inspect
import logging
import platform
from pathlib import Path
from typing import Optional, List
from playwright.async_api import async_playwright, BrowserContext, Page, Error

from app.config import settings

# Import upload function(s) from playwright_copilot.py
try:
    # playwright_copilot provides both a sync and (optionally) an async helper.
    from playwright_copilot import (
        upload_files_from_copilot_folder,
        upload_files_from_copilot_folder_async,
    )
except ImportError:
    # Fallback if import fails
    upload_files_from_copilot_folder = None
    upload_files_from_copilot_folder_async = None

logger = logging.getLogger(__name__)


class CopilotClientError(Exception):
    """Custom exception for Copilot client errors."""

    pass


class CopilotClient:
    """Client for interacting with Microsoft 365 Copilot via Playwright."""

    def __init__(self):
        # Import configuration from existing playwright_copilot.py constants
        self.target_url = getattr(
            settings,
            "copilot_url",
            "https://copilot.cloud.microsoft/?fromCode=cmcv2&redirectId=079013B7710342F5A1FDB755834168FD&auth=2",
        )
        self.chrome_exe = getattr(
            settings,
            "chrome_exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        self.user_data_dir = getattr(settings, "user_data_dir", r".\.Playwright\codes")
        self.downloads_dir = getattr(
            settings, "downloads_dir", r".\.Playwright\downloads"
        )

        # Selectors for Copilot interface
        self.text_input_selector = 'role=combobox[name="Chat Input"]'
        self.send_button_selector = 'role=button[name="Send"]'
        self.copilot_message_selector = '[data-testid="copilot-message-div"]'
        self.copy_button_selector = '[data-testid="CopyButtonTestId"], [data-testid="CopyButtonTestID"], button[aria-label="Copy"]'

        # Persistent session variables
        self.playwright = None
        self.context = None
        self.page = None
        self.is_ready = False
        self.startup_error = None

    def _expand_windows_path(self, path_with_env: str) -> str:
        """Expand %VARS% and normalize Windows path separators."""
        expanded = os.path.expandvars(path_with_env)
        return os.path.normpath(expanded)

    def _ensure_dir(self, path: str) -> None:
        """Ensure directory exists."""
        Path(path).mkdir(parents=True, exist_ok=True)

    async def startup(self) -> bool:
        """
        Start the persistent Playwright session during application startup.

        Returns:
            bool: True if startup successful, False otherwise
        """
        if self.is_ready:
            logger.info("Copilot client already ready")
            return True

        try:
            logger.info("Starting persistent Copilot session...")

            # Launch browser context (this sets self.playwright when called)
            self.context = await self._launch_browser_context()

            # Get the first page or create one
            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = await self.context.new_page()

            # Try to navigate to Copilot and wait for it to be ready.
            # If navigation raises a CopilotClientError due to login, keep the browser open
            # so the operator can sign in manually (persistent profile).
            try:
                await self._navigate_to_copilot(self.page)
            except CopilotClientError as nav_err:
                self.startup_error = str(nav_err)
                self.is_ready = False
                # If the error indicates login is required, leave browser open for manual login.
                if "login" in str(nav_err).lower():
                    logger.warning(
                        "Copilot navigation requires authentication. Leaving browser open for manual login."
                    )
                    # Do not call shutdown(); return False to indicate not yet ready.
                    return False
                # Otherwise, treat as fatal and fall through to cleanup below
                logger.error(f"Copilot navigation failed: {nav_err}")
                await self.shutdown()
                return False

            self.is_ready = True
            self.startup_error = None
            logger.info("Persistent Copilot session is ready and waiting for requests")
            return True

        except CopilotClientError as e:
            # Handle client-specific errors: if they indicate login, keep the browser open.
            self.startup_error = str(e)
            self.is_ready = False
            if "login" in str(e).lower():
                logger.warning(
                    f"Copilot requires login: {e}. Browser left open for manual login."
                )
                return False
            logger.error(f"Failed to start persistent Copilot session: {e}")
            await self.shutdown()
            return False
        except Exception as e:
            self.startup_error = str(e)
            self.is_ready = False
            logger.error(f"Failed to start persistent Copilot session: {e}")
            # Cleanup on unexpected failure
            await self.shutdown()
            return False

    async def shutdown(self) -> None:
        """Shutdown the persistent Playwright session."""
        logger.info("Shutting down persistent Copilot session...")

        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            logger.error(f"Error closing browser context: {e}")

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error stopping Playwright: {e}")

        self.playwright = None
        self.context = None
        self.page = None
        self.is_ready = False
        logger.info("Persistent Copilot session shutdown complete")

    def get_status(self) -> dict:
        """Get the current status of the Copilot client."""
        return {
            "is_ready": self.is_ready,
            "startup_error": self.startup_error,
            "has_browser_context": self.context is not None,
            "has_page": self.page is not None,
        }

    async def _launch_browser_context(self) -> BrowserContext:
        """Launch a persistent browser context with Chrome."""
        logger.info("Starting browser launch process...")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python version: {sys.version}")
        logger.info(
            f"Event loop policy: {type(asyncio.get_event_loop_policy()).__name__}"
        )

        # Fix Windows asyncio event loop policy for subprocess support
        if platform.system() == "Windows":
            try:
                # Set the proper event loop policy for Windows subprocess support
                if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
                    old_policy = asyncio.get_event_loop_policy()
                    logger.info(
                        f"Current event loop policy: {type(old_policy).__name__}"
                    )

                    # Only change if we're not already using ProactorEventLoopPolicy
                    if not isinstance(
                        old_policy, asyncio.WindowsProactorEventLoopPolicy
                    ):
                        logger.info(
                            "Setting WindowsProactorEventLoopPolicy for subprocess support"
                        )
                        asyncio.set_event_loop_policy(
                            asyncio.WindowsProactorEventLoopPolicy()
                        )
                        logger.info("Event loop policy updated successfully")
                    else:
                        logger.info("Already using WindowsProactorEventLoopPolicy")
                else:
                    logger.warning("WindowsProactorEventLoopPolicy not available")
            except Exception as e:
                logger.warning(f"Could not set Windows event loop policy: {e}")

        # Validate Chrome executable path
        chrome_path = Path(self.chrome_exe)
        if not chrome_path.exists():
            raise CopilotClientError(
                f"Chrome executable not found at: {self.chrome_exe}. "
                "Please update CHROME_EXE configuration or install Chrome."
            )

        user_data_dir = self._expand_windows_path(self.user_data_dir)
        downloads_dir = self._expand_windows_path(self.downloads_dir)

        logger.info(f"User data directory: {user_data_dir}")
        logger.info(f"Downloads directory: {downloads_dir}")

        # Ensure directories exist
        self._ensure_dir(user_data_dir)
        self._ensure_dir(downloads_dir)

        logger.info("Starting Playwright...")
        self.playwright = await async_playwright().start()

        try:
            logger.info("Launching Chrome browser context...")
            context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,  # Keep headful for login persistence
                executable_path=self.chrome_exe,
                args=[
                    "--disable-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                accept_downloads=True,
                downloads_path=downloads_dir,
                timeout=60000,  # 60 second timeout for browser launch
            )
            logger.info("Browser context launched successfully")
            return context
        except Exception as e:
            logger.error(f"Browser launch failed: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            await self.playwright.stop()
            self.playwright = None
            raise CopilotClientError(f"Failed to launch browser: {str(e)}")

    async def _navigate_to_copilot(self, page: Page) -> None:
        """Navigate to Copilot URL and wait for page to load."""
        try:
            await page.goto(self.target_url, wait_until="load", timeout=90_000)

            # Check if we're redirected to login page
            current_url = page.url
            if "login.microsoftonline.com" in current_url or "/login" in current_url:
                raise CopilotClientError(
                    "Redirected to Microsoft login page. Please log into Microsoft 365 Copilot manually in Chrome first. "
                    "The persistent browser profile will save your login for future API calls."
                )

            # Wait for the page to be ready - look for the input field
            await page.wait_for_selector(self.text_input_selector, timeout=30_000)

        except Error as e:
            # Check if we're on a login page after the timeout
            try:
                current_url = page.url
                if (
                    "login.microsoftonline.com" in current_url
                    or "/login" in current_url
                ):
                    raise CopilotClientError(
                        "Microsoft 365 Copilot requires authentication. Please log in manually in Chrome first. "
                        "The persistent browser profile will save your login for future API calls."
                    )
            except Exception:
                pass

            raise CopilotClientError(f"Failed to navigate to Copilot: {str(e)}")

    async def _send_prompt(self, page: Page, prompt: str) -> None:
        """Send a prompt to Copilot."""
        try:
            # Find and click the input field
            input_field = page.locator(self.text_input_selector)
            await input_field.wait_for(state="visible", timeout=10_000)
            await input_field.click()

            # Clear any existing text and input the prompt
            await input_field.fill(prompt.strip())
            await input_field.press("Space")  # Trigger UI listeners

            # Find and check the send button state
            send_button = page.locator(self.send_button_selector)
            await send_button.wait_for(state="visible", timeout=10_000)

            # Check if button is disabled (indicates login required)
            is_disabled = await send_button.get_attribute("disabled")
            aria_disabled = await send_button.get_attribute("aria-disabled")

            if is_disabled is not None or aria_disabled == "true":
                # Check current URL for login redirect
                current_url = page.url
                if (
                    "login.microsoftonline.com" in current_url
                    or "/login" in current_url
                ):
                    raise CopilotClientError(
                        "Microsoft 365 Copilot requires authentication. Please log in manually in Chrome first. "
                        "The persistent browser profile will save your login for future API calls."
                    )
                else:
                    raise CopilotClientError(
                        "Send button is disabled. This usually indicates that login is required or the input is invalid."
                    )

            await send_button.click()

        except Error as e:
            # Additional check for login-related errors
            if "disabled" in str(e) or "aria-disabled" in str(e):
                try:
                    current_url = page.url
                    if (
                        "login.microsoftonline.com" in current_url
                        or "/login" in current_url
                    ):
                        raise CopilotClientError(
                            "Microsoft 365 Copilot requires authentication. Please log in manually in Chrome first. "
                            "The persistent browser profile will save your login for future API calls."
                        )
                except Exception:
                    pass

            raise CopilotClientError(f"Failed to send prompt: {str(e)}")

    async def _wait_for_response(
        self, page: Page, initial_message_count: int, timeout: int = 120
    ) -> bool:
        """Wait for Copilot to generate a response."""
        deadline = time.time() + timeout

        # First, wait for a new message container to appear
        try:
            await page.wait_for_function(
                f"document.querySelectorAll('[data-testid=\"copilot-message-div\"]').length > {initial_message_count}",
                timeout=min(15_000, timeout * 1000),
            )
        except Error:
            # Check if we actually got a new message
            current_messages = await page.locator(self.copilot_message_selector).count()
            if current_messages <= initial_message_count:
                return False

        # Then wait for the response to be complete (copy button appears)
        while time.time() < deadline:
            try:
                messages = page.locator(self.copilot_message_selector)
                last_message = messages.last
                copy_button = last_message.locator(self.copy_button_selector).first

                # Check if copy button is visible (indicates response is complete)
                if await copy_button.is_visible():
                    return True

            except Error:
                pass

            # Wait a bit before checking again
            await asyncio.sleep(0.5)

        return False

    async def _extract_latest_response(self, page: Page) -> str:
        """Extract the latest Copilot response from the page."""
        try:
            messages = page.locator(self.copilot_message_selector)
            message_count = await messages.count()

            if message_count == 0:
                raise CopilotClientError("No Copilot messages found on page")

            last_message = messages.last
            await last_message.scroll_into_view_if_needed(timeout=5000)

            # Try to use the copy button first
            copy_button = last_message.locator(self.copy_button_selector).first
            try:
                if await copy_button.is_visible(timeout=5000):
                    # Grant clipboard permissions
                    try:
                        await page.context.grant_permissions(
                            ["clipboard-read", "clipboard-write"], origin=page.url
                        )
                    except Exception:
                        pass  # Permissions might not be needed

                    await copy_button.click()
                    await page.wait_for_timeout(1000)  # Wait for clipboard

                    # Try to read from clipboard
                    try:
                        clipboard_text = await page.evaluate(
                            "navigator.clipboard.readText()"
                        )
                        if clipboard_text and clipboard_text.strip():
                            return clipboard_text.strip()
                    except Exception:
                        pass  # Fall back to DOM text
            except Exception:
                pass  # Fall back to DOM text

            # Fallback: extract text directly from DOM
            response_text = await last_message.inner_text()
            return response_text.strip()

        except Error as e:
            raise CopilotClientError(f"Failed to extract response: {str(e)}")

    async def send_prompt_and_get_response(
        self,
        prompt: str,
        files_to_upload: Optional[List[str]] = None,
        timeout: int = 120,
    ) -> str:
        """
        Send a prompt to Copilot and return the response using the persistent session.
        Updated to input prompt first, then upload files, then send.
        """
        if not prompt or not prompt.strip():
            raise CopilotClientError("Prompt cannot be empty")

        # Check if persistent session is ready
        if not self.is_ready or not self.page:
            raise CopilotClientError(
                "Copilot session not ready. Please check server startup logs. "
                f"Status: {self.get_status()}"
            )

        try:
            logger.info(f"Sending prompt using persistent session: '{prompt[:100]}...'")
            if files_to_upload:
                logger.info(f"Uploading files: {files_to_upload}")

            # Step 1: Input the prompt into the text box (without sending yet)
            await self._input_prompt_only(self.page, prompt)

            # Step 2: Upload files if provided
            if files_to_upload and len(files_to_upload) > 0:
                await self._upload_files_from_copilot_folder(self.page, files_to_upload)

            # Step 3: Click the Send button to submit
            await self._click_send_button(self.page)

            # Wait for and extract the response
            response_text = await self._wait_for_response_and_extract(
                self.page, timeout
            )
            logger.info(
                f"Received response from Copilot ({len(response_text)} characters)"
            )
            return response_text

        except CopilotClientError:
            raise
        except Exception as e:
            import traceback

            logger.error(f"Unexpected error in send_prompt_and_get_response: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise CopilotClientError(f"Unexpected error: {type(e).__name__}: {str(e)}")

    # New helper: Input prompt without sending
    async def _input_prompt_only(self, page: Page, prompt: str) -> None:
        """Input the prompt into the text box without clicking send."""
        try:
            text_input = page.locator(self.text_input_selector)
            await text_input.wait_for(state="visible", timeout=10000)
            await text_input.fill(prompt)
            logger.info(f"Prompt inputted: '{prompt}'")
        except Exception as e:
            raise CopilotClientError(f"Failed to input prompt: {str(e)}")

    # New helper: Click send button
    async def _click_send_button(self, page: Page) -> None:
        """Click the Send button."""
        try:
            send_button = page.locator(self.send_button_selector)
            await send_button.wait_for(state="visible", timeout=10000)
            await send_button.click()
            logger.info("Send button clicked.")
        except Exception as e:
            raise CopilotClientError(f"Failed to click send button: {str(e)}")

    # Updated helper: Wait for response and extract
    async def _wait_for_response_and_extract(self, page: Page, timeout: int) -> str:
        """Wait for the response and extract it."""
        initial_count = await self.page.locator(self.copilot_message_selector).count()
        success = await self._wait_for_response(self.page, initial_count, timeout)
        if not success:
            raise CopilotClientError(
                f"Copilot did not respond within {timeout} seconds. "
                "This might indicate a login is required or the service is unavailable."
            )
        return await self._extract_latest_response(self.page)

    async def _upload_files_from_copilot_folder(
        self, page: Page, file_list: List[str]
    ) -> None:
        """
        Upload files from Copilot SharePoint folder using the file picker.

        Args:
            page: Playwright page instance
            file_list: List of file names to upload

        Raises:
            CopilotClientError: If upload fails
        """
        # Prefer an explicitly-provided async helper if available
        if (
            not upload_files_from_copilot_folder
            and not upload_files_from_copilot_folder_async
        ):
            raise CopilotClientError(
                "Upload function not available. Check playwright_copilot.py import."
            )

        try:
            logger.info(f"Uploading files from Copilot folder: {file_list}")

            # If an async-specific helper is provided, prefer it
            if upload_files_from_copilot_folder_async and inspect.iscoroutinefunction(
                upload_files_from_copilot_folder_async
            ):
                await upload_files_from_copilot_folder_async(page, file_list)
                logger.info("File upload (async helper) completed successfully")
                return

            # If the imported helper is an async function, await it
            if upload_files_from_copilot_folder and inspect.iscoroutinefunction(
                upload_files_from_copilot_folder
            ):
                await upload_files_from_copilot_folder(page, file_list)
                logger.info("File upload (async function) completed successfully")
                return

            # Otherwise treat it as a synchronous helper and run in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, upload_files_from_copilot_folder, page, file_list
            )
            logger.info("File upload (sync helper via executor) completed successfully")

        except Exception as e:
            logger.error(f"Failed to upload files: {str(e)}")
            raise CopilotClientError(f"File upload failed: {str(e)}")


# Global client instance
copilot_client = CopilotClient()
