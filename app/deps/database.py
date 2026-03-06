import logging
from app.db.mongo import get_db

logger = logging.getLogger(__name__)


def get_location_collection():
    logger.info("[get_location_collection] Getting locations collection")
    db = get_db()
    return db["locations"]
