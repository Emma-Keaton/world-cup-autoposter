"""
FastAPI application for the World Cup Autoposter backend.
"""
import os
import asyncio

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from contextlib import asynccontextmanager

from app.core.database import init_db, close_db, get_db
from app.core.config import settings
from app.api import (
    content,
    scraping,
    rendering,
    competitors,
    analytics,
    health,
    clipper,
    thumbnailer,
    notifications,
    settings,
    system_info,
    ab_testing,
)
from app.services.error_notifier import get_error_notifier, ErrorSeverity, notify_error
from app.core.auth import setup_authentication
from app.core.production import validate_on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler with validation."""
    # Startup
    logger.info("Starting World Cup Autoposter API...")
    
    # Validate configuration
    validate_on_startup()

    # Initialize database (creates all tables)
    await init_db()
    logger.info("Database initialized")

    # Initialize services
    try:
        from app.core.settings_service import get_settings_service
        settings_service = get_settings_service()
        await settings_service.initialize()
        logger.info("Settings service initialized")
        
        from app.core.rate_limiter import get_rate_limiter
        get_rate_limiter()
        logger.info("Rate limiter initialized")
        
        from app.core.scheduler import get_scheduler
        get_scheduler()
        logger.info("Content scheduler initialized")
        
        from app.core.auto_approval import get_approval_engine
        get_approval_engine()
        logger.info("Auto-approval engine initialized")
    except Exception as e:
        logger.warning(f"Service initialization error: {e}")

    # Initialize optional services
    try:
        error_notifier = get_error_notifier()
        await error_notifier.initialize()
        logger.info("Error notification service initialized")
    except Exception as e:
        logger.warning(f"Error notifier not available: {e}")

    yield

    # Shutdown
    await close_db()
    try:
        from app.publisher.buffer_publisher import get_buffer_publisher
        await get_buffer_publisher().close()
    except Exception:
        pass
    logger.info("Application shutdown complete")


app = FastAPI(
    title="World Cup Autoposter API",
    description="Autonomous football content creation system for Instagram Reels and YouTube Shorts",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Don't redirect /api/health to /api/health/
)

# CORS middleware (production-ready)
production_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
] + [origin.strip() for origin in production_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup API key authentication
setup_authentication(app)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging."""
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"Response: {response.status_code}")
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled error: {exc}")
    
    # Send WhatsApp alert for critical errors
    try:
        # Determine severity based on error type
        error_name = type(exc).__name__
        severity = ErrorSeverity.HIGH if error_name in [
            "DatabaseError", "ConnectionError", "TimeoutError",
            "AuthenticationError", "PaymentError"
        ] else ErrorSeverity.MEDIUM
        
        # Send notification in background (don't block response)
        asyncio.create_task(notify_error(
            error=exc,
            severity=severity,
            context="global_exception_handler",
            extra_info={"path": str(request.url.path), "method": request.method}
        ))
    except Exception as notification_error:
        # Don't let notification errors bubble up
        logger.error(f"Failed to send error notification: {notification_error}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(content.router, prefix="/api/content", tags=["Content"])
app.include_router(scraping.router, prefix="/api/scraping", tags=["Scraping"])
app.include_router(rendering.router, prefix="/api/rendering", tags=["Rendering"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["Competitors"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(clipper.router, prefix="/api/clipper", tags=["YouTube Clipper"])
app.include_router(thumbnailer.router, prefix="/api/thumbnailer", tags=["Thumbnail Generator"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(system_info.router, prefix="/api/system", tags=["System"])
app.include_router(ab_testing.router, prefix="/api/ab-testing", tags=["A/B Testing"])


# Serve static frontend files from dist folder
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Get the frontend directory path (works for both local dev and Render deployment)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dist_path = os.path.join(base_dir, "frontend", "dist")

# Serve static assets and index.html for SPA
if os.path.exists(frontend_dist_path):
    # Mount static assets (JS, CSS, images from dist) - this handles /assets/*
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")

    # Serve logo
    @app.get("/logo.jpeg")
    async def serve_logo():
        logo_path = os.path.join(frontend_dist_path, "logo.jpeg")
        if os.path.exists(logo_path):
            return FileResponse(logo_path)
        return {"error": "Logo not found"}

    # Serve root index.html
    @app.get("/")
    @app.head("/")  # Support HEAD requests for health checks
    async def serve_root():
        index_path = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type="text/html")
        return {"message": "Frontend not built"}


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }
