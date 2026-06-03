"""
Production configuration and validation.
Validates required settings and provides production-ready defaults.
"""
import os
import sys
from pathlib import Path
from loguru import logger


class ProductionValidator:
    """Validates production configuration requirements."""
    
    REQUIRED_ENV_VARS = [
        # Core
        "APP_ENV",
        
        # AI/LLM
        "NVIDIA_API_KEY",
        
        # Database (uses SQLite if not set, but warn for production)
        # "DATABASE_URL",  # Optional - defaults to SQLite
    ]
    
    SENSITIVE_ENV_VARS = [
        "NVIDIA_API_KEY",
        "BUFFER_API_KEY",
        "META_ACCESS_TOKEN",
        "YOUTUBE_API_KEY",
        "OPENAI_API_KEY",
        "WHATSAPP_PHONE_NUMBER",
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_required(self) -> bool:
        """Validate required environment variables."""
        for var in self.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if not value or value.strip() == "":
                self.errors.append(f"Missing required environment variable: {var}")
        return len(self.errors) == 0
    
    def validate_production(self) -> bool:
        """Additional validation for production environment."""
        app_env = os.getenv("APP_ENV", "development")
        
        if app_env == "production":
            # Check for production database
            db_url = os.getenv("DATABASE_URL", "")
            if "sqlite" in db_url.lower():
                self.warnings.append(
                    "Using SQLite in production. Consider PostgreSQL for better performance."
                )
            
            # Check for debug mode
            if os.getenv("DEBUG", "false").lower() == "true":
                self.warnings.append("DEBUG mode is enabled in production. This is a security risk.")
        
        # Check FFmpeg
        if not self._check_ffmpeg():
            self.warnings.append(
                "FFmpeg not found. Video processing will fail. Install FFmpeg or ensure it's in PATH."
            )
        
        return True
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        import shutil
        return shutil.which("ffmpeg") is not None
    
    def validate(self) -> bool:
        """Run all validations."""
        self.validate_required()
        self.validate_production()
        
        # Log results
        if self.errors:
            logger.error("❌ Configuration validation failed:")
            for error in self.errors:
                logger.error(f"  - {error}")
        
        if self.warnings:
            logger.warning("⚠️ Configuration warnings:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        if not self.errors:
            logger.info("✅ Configuration validation passed")
        
        return len(self.errors) == 0
    
    def get_status(self) -> dict:
        """Get validation status as dict."""
        self.validate()
        
        # Mask sensitive values
        env_status = {}
        for var in self.REQUIRED_ENV_VARS + self.SENSITIVE_ENV_VARS:
            value = os.getenv(var, "")
            if var in self.SENSITIVE_ENV_VARS and value:
                # Mask middle characters
                masked = value[:3] + "***" + value[-3:] if len(value) > 6 else "***"
                env_status[var] = {"configured": bool(value), "value": masked}
            else:
                env_status[var] = {"configured": bool(value), "value": value}
        
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "environment_variables": env_status,
            "ffmpeg_available": self._check_ffmpeg(),
        }


# Global validator
_validator = ProductionValidator()


def get_validator() -> ProductionValidator:
    """Get the global validator instance."""
    return _validator


def validate_on_startup() -> bool:
    """Validate configuration on application startup."""
    validator = get_validator()
    is_valid = validator.validate()
    
    if not is_valid:
        logger.critical("Application startup aborted due to configuration errors.")
        sys.exit(1)
    
    return is_valid