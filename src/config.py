"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JSON_SORT_KEYS = False

    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "intelligent_helpdesk")

    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")

    MODELS_DIR = BASE_DIR / "models"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}