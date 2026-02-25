from bson import ObjectId
from datetime import datetime, timezone
from app.services.embeddings import embed_text


class LocationRepository:
    def __init__(self, collection):
        self.collection = collection

    def _to_out(self, doc: dict) -> dict:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        return doc

    async def create(self, data: dict) -> str:
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
        return str(result.inserted_id)

    async def list_all(
        self, limit: int = 200, include_deleted: bool = False
    ) -> list[dict]:
        query = {} if include_deleted else {"is_deleted": {"$ne": True}}
        docs = []
        async for d in self.collection.find(query).limit(limit):
            docs.append(self._to_out(d))
        return docs

    async def get(self, location_id: str, include_deleted: bool = False) -> dict | None:
        if not ObjectId.is_valid(location_id):
            return None
        query = {"_id": ObjectId(location_id)}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}
        doc = await self.collection.find_one(query)
        return self._to_out(doc) if doc else None

    async def update(self, location_id: str, data: dict) -> bool:
        if not ObjectId.is_valid(location_id):
            return False

        # Only update provided fields
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return False

        if "description" in data:
            data["embedding"] = await embed_text(data["description"])

        if "latitude" in data or "longitude" in data:
            # We need both to update the point, or we fetch from DB
            # For simplicity, if either is provided, we expect both or we'd need to fetch
            # But in typical Pydantic update, they might be partial.
            # Let's check if both are in data. If not, we might need current values.
            # To be safe, if either is updated, we should probably ensure the point is updated.
            # Let's fetch the current doc if only one is provided.
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
        return result.matched_count > 0

    async def soft_delete(self, location_id: str) -> bool:
        if not ObjectId.is_valid(location_id):
            return False
        now = datetime.now(timezone.utc).isoformat()
        result = await self.collection.update_one(
            {"_id": ObjectId(location_id), "is_deleted": {"$ne": True}},
            {"$set": {"is_deleted": True, "deleted_at": now}},
        )
        return result.matched_count > 0
