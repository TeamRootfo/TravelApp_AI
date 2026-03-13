import logging
from app.db.mongo import get_db

logger = logging.getLogger(__name__)


def get_location_collection():
    logger.info("[get_location_collection] Getting locations collection")
    db = get_db()
    return db["locations"]


def get_package_collection():
    logger.info("[get_package_collection] Getting packages collection")
    db = get_db()
    return db["packages"]
