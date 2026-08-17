"""MongoDB connection and index setup."""

import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

_client = None
_db = None


def init_db(app):
    """Open the MongoDB connection and create indexes."""
    global _client, _db

    _client = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=3000,
    )
    _db = _client[app.config["MONGO_DB_NAME"]]

    try:
        _client.admin.command("ping")
        logger.info("Connected to MongoDB: %s", app.config["MONGO_DB_NAME"])
    except ServerSelectionTimeoutError:
        logger.error("MongoDB unreachable at %s", app.config["MONGO_URI"])
        raise

    _create_indexes()
    return _db


def _create_indexes():
    """Create the indexes required by the application."""
    _db.users.create_index([("email", ASCENDING)], unique=True)
    _db.tickets.create_index([("created_at", DESCENDING)])
    _db.tickets.create_index([("assigned_queue", ASCENDING),
                              ("priority", ASCENDING)])
    _db.logs.create_index([("timestamp", DESCENDING)])
    logger.info("MongoDB indexes ensured")


def get_db():
    """Return the active database handle."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db