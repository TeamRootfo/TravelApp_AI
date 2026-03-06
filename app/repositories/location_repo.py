import logging
from bson import ObjectId
from datetime import datetime, timezone
from app.services.embeddings import embed_text
from motor.motor_asyncio import AsyncIOMotorCollection

logger = logging.getLogger(__name__)


class LocationRepository:
    def __init__(self, collection):
        self.collection = collection
        logger.info("[LocationRepository.__init__] Initialized repository")

    def _to_out(self, doc: dict) -> dict:
        logger.info(f"[_to_out] Converting document ID: {doc.get('_id')}")
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        return doc

    async def get_all_tags(self) -> list[str]:
        logger.info("[get_all_tags] Fetching all tags")
        tags = await self.collection.distinct("tags", {"is_deleted": {"$ne": True}})
        # normalize (optional)
        tags = sorted(
            {t.strip().lower() for t in tags if isinstance(t, str) and t.strip()}
        )
        return tags

    async def create(self, data: dict) -> str:
        logger.info(f"[create] Creating location: {data.get('name')}")
        # soft delete defaults
        data.setdefault("is_deleted", False)
        data.setdefault("deleted_at", None)

        if "latitude" in data and "longitude" in data:
            data["location"] = {
                "type": "Point",
                "coordinates": [data["longitude"], data["latitude"]],
            }

        data["embedding"] = await embed_text(data.get("description", ""))

        result = await self.collection.insert_one(data)
        logger.info(f"[create] Created location ID: {result.inserted_id}")
        return str(result.inserted_id)

    async def list_all(
        self, limit: int = 200, include_deleted: bool = False
    ) -> list[dict]:
        logger.info(
            f"[list_all] Listing locations: limit={limit}, include_deleted={include_deleted}"
        )
        query = {} if include_deleted else {"is_deleted": {"$ne": True}}
        docs = []
        async for d in self.collection.find(query).limit(limit):
            docs.append(self._to_out(d))
        return docs

    async def get(self, location_id: str, include_deleted: bool = False) -> dict | None:
        logger.info(f"[get] Fetching location ID: {location_id}")
        if not ObjectId.is_valid(location_id):
            return None
        query = {"_id": ObjectId(location_id)}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}
        doc = await self.collection.find_one(query)
        return self._to_out(doc) if doc else None

    async def update(self, location_id: str, data: dict) -> bool:
        logger.info(f"[update] Updating location ID: {location_id}")
        if not ObjectId.is_valid(location_id):
            return False

        # Only update provided fields
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return False

        if "description" in data:
            data["embedding"] = await embed_text(data["description"])

        if "latitude" in data or "longitude" in data:

            if "latitude" not in data or "longitude" not in data:
                current = await self.collection.find_one({"_id": ObjectId(location_id)})
                if current:
                    lat = data.get("latitude", current.get("latitude"))
                    lon = data.get("longitude", current.get("longitude"))
                    data["location"] = {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    }
            else:
                data["location"] = {
                    "type": "Point",
                    "coordinates": [data["longitude"], data["latitude"]],
                }

        result = await self.collection.update_one(
            {"_id": ObjectId(location_id), "is_deleted": {"$ne": True}},
            {"$set": data},
        )
        logger.info(
            f"[update] Update status for {location_id}: {result.matched_count > 0}"
        )
        return result.matched_count > 0

    async def soft_delete(self, location_id: str) -> bool:
        logger.info(f"[soft_delete] Soft deleting location ID: {location_id}")
        if not ObjectId.is_valid(location_id):
            return False
        now = datetime.now(timezone.utc).isoformat()
        result = await self.collection.update_one(
            {"_id": ObjectId(location_id), "is_deleted": {"$ne": True}},
            {"$set": {"is_deleted": True, "deleted_at": now}},
        )
        logger.info(
            f"[soft_delete] Soft delete status for {location_id}: {result.matched_count > 0}"
        )
        return result.matched_count > 0

    # async def nearby(
    #     self,
    #     latitude: float,
    #     longitude: float,
    #     max_distance_m: int = 1000,
    #     limit: int = 20,

    # ) -> list[dict]:
    #     query = {
    #         "is_deleted": {"$ne": True},
    #         "location": {
    #             "$near": {
    #                 "$geometry": {
    #                     "type": "Point",
    #                     "coordinates": [longitude, latitude],  # IMPORTANT ORDER
    #                 },
    #                 "$maxDistance": max_distance_m,
    #             }
    #         },
    #     }

    #     # Only return name and description fields
    #     projection = {"name": 1, "latitude": 1, "longitude": 1, "_id": 0}

    #     try:
    #         docs = []
    #         async for d in self.collection.find(query, projection).limit(limit):
    #             docs.append({
    #                 "name": d.get("name"),
    #                 "latitude": d.get("latitude"),
    #                 "longitude": d.get("longitude"),
    #             })

    #         return docs
    #     except Exception as e:
    #         print(f"Error in nearby query: {e}")
    #         return []

    async def fetch_for_ranking(self, limit: int = 500) -> list[dict]:
        logger.info(
            f"[fetch_for_ranking] Fetching locations for ranking: limit={limit}"
        )
        projection = {
            "name": 1,
            "latitude": 1,
            "longitude": 1,
            "tags": 1,
            "embedding": 1,
        }
        docs = []
        async for d in self.collection.find(
            {"is_deleted": {"$ne": True}}, projection
        ).limit(limit):
            docs.append(self._to_out(d))
        return docs

    async def nearby(
        self,
        anchor_id: str,
        latitude: float,
        longitude: float,
        max_distance_m: int = 5000,
        limit: int = 200,
        include_deleted: bool = False,
    ) -> list[dict]:
        logger.info(f"[nearby] Finding nearby locations around: {anchor_id}")
        query = {
            "_id": {"$ne": ObjectId(anchor_id)},
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                    "$maxDistance": max_distance_m,
                }
            },
        }
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}

        projection = {"embedding": 0}
        docs = []
        async for d in self.collection.find(query, projection).limit(limit):
            docs.append(self._to_out(d))
        return docs
