"""Main FastAPI application with middleware and router registration."""

import logging
import uuid
import asyncio
import platform
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time

from app.config import settings
from app.routers import process
from app.startup import initialize_application
from app.services.copilot_client import copilot_client

# Initialize Windows asyncio compatibility BEFORE any other imports that might use asyncio
initialize_application()


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    cors_origins = settings.parse_cors_origins()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for origins: {cors_origins}")

    # Add trusted host middleware for security
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # In production, this should be more restrictive
    )

    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests with timing and request ID."""
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Add request ID to request state for use in endpoints
        request.state.request_id = request_id

        # Log request start
        logger.info(
            f"Request started - ID: {request_id} | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Query: {request.url.query} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log request completion
        logger.info(
            f"Request completed - ID: {request_id} | "
            f"Status: {response.status_code} | "
            f"Duration: {duration_ms}ms"
        )

        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id

        return response

    # Include routers
    app.include_router(process.router, tags=["processing"])

    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        """Log application startup and initialize persistent Copilot session."""
        logger.info(f"Starting {settings.api_title} v{settings.api_version}")
        
        # Configure Windows event loop policy for Playwright subprocess support
        if platform.system() == "Windows":
            try:
                current_policy = asyncio.get_event_loop_policy()
                logger.info(f"Current event loop policy: {type(current_policy).__name__}")
                
                if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
                    if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
                        logger.info("Setting WindowsProactorEventLoopPolicy for Playwright subprocess support")
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                        new_policy = asyncio.get_event_loop_policy()
                        logger.info(f"Event loop policy updated to: {type(new_policy).__name__}")
                    else:
                        logger.info("Already using WindowsProactorEventLoopPolicy")
                else:
                    logger.warning("WindowsProactorEventLoopPolicy not available")
            except Exception as e:
                logger.error(f"Failed to configure Windows event loop policy: {e}")
        
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Max file size: {settings.max_file_size_mb}MB")
        logger.info(f"Max files per request: {settings.max_files}")
        logger.info(
            f"Allowed MIME types: {', '.join(sorted(settings.allowed_mime_types))}"
        )
        
        # Start persistent Copilot session
        logger.info("Initializing persistent Copilot session...")
        try:
            success = await copilot_client.startup()
            if success:
                logger.info("✓ Persistent Copilot session initialized successfully")
            else:
                logger.warning("⚠ Persistent Copilot session failed to initialize")
                logger.warning("  API will still start, but Copilot requests will fail until login is completed")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Copilot session: {e}")
            logger.warning("  API will still start, but Copilot requests will fail")
        
        logger.info("Application startup complete")

    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Log application shutdown and cleanup Copilot session."""
        logger.info("Shutting down application...")
        
        # Shutdown persistent Copilot session
        try:
            await copilot_client.shutdown()
            logger.info("✓ Copilot session shutdown complete")
        except Exception as e:
            logger.error(f"Error during Copilot session shutdown: {e}")
        
        logger.info("Application shutdown complete")

    return app


# Create the application instance
app = create_app()


# Health check at root for simple monitoring
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to health check."""
    return {
        "message": f"Welcome to {settings.api_title}",
        "docs": "/docs",
        "health": "/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
