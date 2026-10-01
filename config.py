"""Application configuration loaded from environment variables.

Single-responsibility: this module's only job is to expose a typed,
validated view of the process environment. No business logic lives here.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Centralized, environment-driven application configuration."""

    MYSQL_HOST: str = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.environ.get("MYSQL_USER", "lms_user")
    MYSQL_PASSWORD: str = os.environ.get("MYSQL_PASSWORD", "lms_password")
    MYSQL_DB: str = os.environ.get("MYSQL_DB", "lms_db")

    JWT_SECRET: str = os.environ.get("JWT_SECRET", "change-me-in-production")
    JWT_EXP_MINUTES: int = int(os.environ.get("JWT_EXP_MINUTES", "60"))

    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    @classmethod
    def as_dict(cls) -> dict:
        """Return non-secret config values, safe for logging/debugging."""
        return {
            "MYSQL_HOST": cls.MYSQL_HOST,
            "MYSQL_PORT": cls.MYSQL_PORT,
            "MYSQL_DB": cls.MYSQL_DB,
            "JWT_EXP_MINUTES": cls.JWT_EXP_MINUTES,
            "LOG_LEVEL": cls.LOG_LEVEL,
        }


# Module-level singleton instance, imported everywhere else in the app.
config = Config()
