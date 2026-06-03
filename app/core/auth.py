"""
API Key Authentication Middleware.
Protects API endpoints with simple API key authentication.
"""
import os
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    
    Validates that requests include a valid API key in the header:
    X-API-Key: <your-api-key>
    
    Excludes certain paths from authentication.
    """
    
    def __init__(
        self,
        app,
        api_key_env: str = "API_KEY",
        excluded_paths: list = None,
    ):
        super().__init__(app)
        self.api_key = os.getenv(api_key_env, "")
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/api/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Check if path is excluded
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        # Validate API key
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing API key. Include X-API-Key header."},
            )
        
        if self.api_key and api_key != self.api_key:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid API key."},
            )
        
        # API key is valid (or not configured)
        return await call_next(request)


def setup_authentication(app: FastAPI) -> None:
    """Set up authentication middleware on the app."""
    
    # Check if API key is configured
    api_key = os.getenv("API_KEY", "")
    
    if api_key:
        app.add_middleware(
            APIKeyMiddleware,
            api_key_env="API_KEY",
            excluded_paths=[
                "/",
                "/health",
                "/api/health",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/frontend/",
            ],
        )
        print("[OK] API authentication enabled (API_KEY configured)")
    else:
        print("[INFO] API authentication disabled (API_KEY not set)")
        print("   Set API_KEY environment variable to enable authentication")