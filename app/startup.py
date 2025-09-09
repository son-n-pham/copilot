"""Application startup configuration for Windows asyncio compatibility."""

import asyncio
import platform
import logging

logger = logging.getLogger(__name__)


def configure_windows_event_loop_policy():
    """
    Configure Windows event loop policy for subprocess support.

    This must be called before any asyncio operations that might create subprocesses,
    particularly before Playwright operations.
    """
    if platform.system() == "Windows":
        try:
            current_policy = asyncio.get_event_loop_policy()
            logger.info(f"Current event loop policy: {type(current_policy).__name__}")

            if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
                if not isinstance(
                    current_policy, asyncio.WindowsProactorEventLoopPolicy
                ):
                    logger.info(
                        "Setting WindowsProactorEventLoopPolicy for Playwright subprocess support"
                    )
                    asyncio.set_event_loop_policy(
                        asyncio.WindowsProactorEventLoopPolicy()
                    )

                    # Verify the change
                    new_policy = asyncio.get_event_loop_policy()
                    logger.info(
                        f"Event loop policy updated to: {type(new_policy).__name__}"
                    )

                    # Create a new event loop to ensure it uses the new policy
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    logger.info("New event loop created with ProactorEventLoopPolicy")

                    return True
                else:
                    logger.info("Already using WindowsProactorEventLoopPolicy")
                    return True
            else:
                logger.warning("WindowsProactorEventLoopPolicy not available")
                return False
        except Exception as e:
            logger.error(f"Failed to configure Windows event loop policy: {e}")
            return False
    else:
        logger.info(
            f"Non-Windows platform ({platform.system()}), no event loop policy change needed"
        )
        return True


def initialize_application():
    """Initialize application with proper asyncio configuration."""
    logger.info("Initializing application with Windows asyncio compatibility...")

    success = configure_windows_event_loop_policy()

    if success:
        logger.info("Application initialization completed successfully")
    else:
        logger.warning("Application initialization completed with warnings")

    return success
