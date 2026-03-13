import logging
from bson import ObjectId
from datetime import datetime, timezone
from app.services.embeddings import embed_text
from motor.motor_asyncio import AsyncIOMotorCollection
from app.models.package import Package, Day, Stop, PackageState

logger = logging.getLogger(__name__)


class PackageRepository:
    def __init__(
        self,
        collection: AsyncIOMotorCollection,
    ):
        self.collection = collection
        logger.info("[PackageRepository.__init__] Initialized repository")

    def _to_out(self, doc: dict) -> dict:
        logger.info(f"[_to_out] Converting document ID: {doc.get('_id')}")
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        return doc

    async def create(self, data: dict) -> str:
        logger.info(f"[create] Creating package: {data.get('name')}")
        # soft delete defaults
        data.setdefault("is_deleted", False)
        data.setdefault("deleted_at", None)

        result = await self.collection.insert_one(data)
        logger.info(f"[create] Created package ID: {result.inserted_id}")
        return str(result.inserted_id)

    async def list_all(
        self, limit: int = 200, include_deleted: bool = False
    ) -> list[dict]:
        logger.info(
            f"[list_all] Listing packages: limit={limit}, include_deleted={include_deleted}"
        )
        query = {} if include_deleted else {"is_deleted": {"$ne": True}}
        docs = []
        async for d in self.collection.find(query).limit(limit):
            docs.append(self._to_out(d))
        return docs

    async def get_by_id(
        self, package_id: str, include_deleted: bool = False
    ) -> dict | None:
        logger.info(f"[get] Fetching package ID: {package_id}")
        if not ObjectId.is_valid(package_id):
            return None
        query = {"_id": ObjectId(package_id)}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}
        doc = await self.collection.find_one(query)
        return self._to_out(doc) if doc else None

    async def filtered_packages(
        self,
        min_price: float,
        max_price: float,
        participant_count: int,
        limit: int = 100,
    ) -> list[dict]:
        logger.info(
            f"[filtered] filtered packages: min_price={min_price}, max_price={max_price}, participant_count={participant_count}, limit={limit}"
        )
        query = {
            "is_deleted": {"$ne": True},
            "price": {"$gte": min_price, "$lte": max_price},
            "states": {"$ne": PackageState.DEACTIVE, "$ne": PackageState.PENDING},
            "max_number_of_participants": {"$gte": participant_count},
        }
        packages = []
        async for d in self.collection.find(query).limit(limit):
            packages.append(self._to_out(d))

        return packages
