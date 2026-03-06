import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    client: AsyncIOMotorClient | None = None


mongodb = MongoDB()


async def connect_to_mongo():
    logger.info("[connect_to_mongo] Connecting to MongoDB")
    mongodb.client = AsyncIOMotorClient(settings.MONGO_URI)

    await mongodb.client.admin.command("ping")
    logger.info("[connect_to_mongo] MongoDB Connected")
    await create_indexes()


async def create_indexes():
    logger.info("[create_indexes] Creating indexes")
    db = mongodb.client[settings.MONGO_DB]

    logger.info(f"[create_indexes] DB: {db.name}")
    logger.info(f"[create_indexes] Collections: {await db.list_collection_names()}")

    idx_name = await db["locations"].create_index([("location", "2dsphere")])
    logger.info(f"[create_indexes] Created/Existing index name: {idx_name}")

    info = await db["locations"].index_information()
    logger.info(f"[create_indexes] Index info: {info}")


async def close_mongo_connection():
    logger.info("[close_mongo_connection] Closing MongoDB connection")
    if mongodb.client:
        mongodb.client.close()
        logger.info("[close_mongo_connection] MongoDB Disconnected")


def get_db():
    logger.info("[get_db] Getting database instance")
    return mongodb.client[settings.MONGO_DB]
