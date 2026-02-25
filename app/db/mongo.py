from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None


mongodb = MongoDB()


async def connect_to_mongo():
    mongodb.client = AsyncIOMotorClient(settings.MONGO_URI)

    await mongodb.client.admin.command("ping")
    print("MongoDB Connected")
    await create_indexes()


async def create_indexes():
    db = mongodb.client[settings.MONGO_DB]

    print("DB:", db.name)
    print("Collections:", await db.list_collection_names())

    idx_name = await db["locations"].create_index([("location", "2dsphere")])
    print("Created/Existing index name:", idx_name)

    info = await db["locations"].index_information()
    print("Index info:", info)


async def close_mongo_connection():
    if mongodb.client:
        mongodb.client.close()
        print("MongoDB Disconnected")


def get_db():
    return mongodb.client[settings.MONGO_DB]
