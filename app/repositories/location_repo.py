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
