import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


MONGO_URI = settings.MONGO_URI
DB_NAME = settings.MONGO_DB
COLLECTION_NAME = "locations"


async def check_vector_indexes():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    indexes = await collection.list_search_indexes().to_list(length=None)

    if not indexes:
        print("❌ No search/vector indexes found.")
        return

    print("✅ Found Search Indexes:\n")

    for idx in indexes:
        print("Index Name:", idx.get("name"))
        print("Status:", idx.get("status"))
        print("Type:", idx.get("type"))
        print("Definition:", idx.get("definition"))
        print("-" * 40)


async def test_vector_search():
    client = AsyncIOMotorClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]

    # Replace 1536 with your real embedding dimension
    query_vector = [0.1] * 1536

    pipeline = [
        {
            "$vectorSearch": {
                "index": "location_vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 20,
                "limit": 5,
            }
        },
        {
            "$project": {
                "name": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = await collection.aggregate(pipeline).to_list(length=5)
    print("Results:", results)

if __name__ == "__main__":
    asyncio.run(check_vector_indexes())
    asyncio.run(test_vector_search())
