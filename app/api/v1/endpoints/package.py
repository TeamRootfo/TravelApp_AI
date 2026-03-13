import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from app.models.package import PackageRecommandRequest
from app.models.intent import IntentAutoAreaRequest, MatchOut
from app.models.planner import PlannerRequest
from app.models.planner import TagSuggestRequest
from app.repositories.location_repo import LocationRepository
from app.repositories.package_repo import PackageRepository
from app.services.package.package_recommander import recommended_packages
from app.deps.database import get_package_collection
from app.deps.database import get_location_collection
from app.services.tagging import suggest_tags_from_description

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/package", tags=["packages"])


def get_package_repo(collection=Depends(get_package_collection)) -> PackageRepository:
    logger.info("[get_repo] Getting PackageRepository instance")
    return PackageRepository(collection)


def get_location_repo(
    collection=Depends(get_location_collection),
) -> LocationRepository:
    logger.info("[get_repo] Getting LocationRepository instance")
    return LocationRepository(collection)


@router.post("/recommanded-packages")
async def package_recommander(
    payload: PackageRecommandRequest,
    repo: PackageRepository = Depends(get_package_repo),
    location_repo: LocationRepository = Depends(get_location_repo),
):
    return await recommended_packages(
        repo=repo,
        location_repo=location_repo,
        min_price=payload.min_price,
        max_price=payload.max_price,
        description=payload.description,
        participant_count=payload.participant_count,
        limit=payload.limit,
    )


@router.post("/seed")
async def seed_packages(
    collection: Any = Depends(get_package_collection),
    location_collection: Any = Depends(get_location_collection),
):
    # Fetch all predefined location names to map to their ObjectIds
    places_names = [
        "Colombo",
        "Kandy",
        "Sigiriya",
        "Yala National Park",
        "Negombo Beach",
        "Dambulla",
        "Galle Face Green",
    ]
    places_cursor = location_collection.find({"name": {"$in": places_names}})
    places_docs = await places_cursor.to_list(length=100)

    # Create a dictionary to map location names to their ObjectIds
    loc_map = {doc["name"]: str(doc["_id"]) for doc in places_docs}

    def get_id(name: str) -> str:
        return loc_map.get(name, f"fallback_id_{name.replace(' ', '_').lower()}")

    dummy_packages = [
        # Original package with dynamic IDs
        {
            "number_of_days": 2,
            "price": 250.0,
            "rating": 4,
            "max_number_of_participants": 10,
            "owner_id": "user123",
            "owner": "Travel Lanka",
            "places": [get_id("Sigiriya"), get_id("Dambulla")],
            "states": "active",
            "is_deleted": False,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "days": [
                {
                    "day": 1,
                    "is_last_day": False,
                    "start_name": "Colombo",
                    "start_id": get_id("Colombo"),
                    "end_name": "Sigiriya",
                    "end_id": get_id("Sigiriya"),
                    "stops": [
                        {
                            "order": 1,
                            "name": "Dambulla",
                            "location_id": get_id("Dambulla"),
                        }
                    ],
                },
                {
                    "day": 2,
                    "is_last_day": True,
                    "start_name": "Sigiriya",
                    "start_id": get_id("Sigiriya"),
                    "end_name": "Colombo",
                    "end_id": get_id("Colombo"),
                    "stops": [],
                },
            ],
        },
        # New Package 1: Colombo to Kandy
        {
            "number_of_days": 1,
            "price": 80.0,
            "rating": 5,
            "max_number_of_participants": 15,
            "owner_id": "user124",
            "owner": "City Explorer",
            "places": [get_id("Colombo"), get_id("Kandy")],
            "states": "active",
            "is_deleted": False,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "days": [
                {
                    "day": 1,
                    "is_last_day": True,
                    "start_name": "Colombo",
                    "start_id": get_id("Colombo"),
                    "end_name": "Kandy",
                    "end_id": get_id("Kandy"),
                    "stops": [
                        {
                            "order": 1,
                            "name": "Galle Face Green",
                            "location_id": get_id("Galle Face Green"),
                        }
                    ],
                }
            ],
        },
        # New Package 2: Safari Adventure
        {
            "number_of_days": 2,
            "price": 350.0,
            "rating": 5,
            "max_number_of_participants": 8,
            "owner_id": "user125",
            "owner": "WildLife Lanka",
            "places": [get_id("Yala National Park")],
            "states": "active",
            "is_deleted": False,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "days": [
                {
                    "day": 1,
                    "is_last_day": False,
                    "start_name": "Colombo",
                    "start_id": get_id("Colombo"),
                    "end_name": "Yala National Park",
                    "end_id": get_id("Yala National Park"),
                    "stops": [],
                },
                {
                    "day": 2,
                    "is_last_day": True,
                    "start_name": "Yala National Park",
                    "start_id": get_id("Yala National Park"),
                    "end_name": "Colombo",
                    "end_id": get_id("Colombo"),
                    "stops": [],
                },
            ],
        },
        # New Package 3: Beach Relax
        {
            "number_of_days": 1,
            "price": 60.0,
            "rating": 4,
            "max_number_of_participants": 20,
            "owner_id": "user123",
            "owner": "Travel Lanka",
            "places": [get_id("Negombo Beach")],
            "states": "active",
            "is_deleted": False,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "days": [
                {
                    "day": 1,
                    "is_last_day": True,
                    "start_name": "Colombo",
                    "start_id": get_id("Colombo"),
                    "end_name": "Negombo Beach",
                    "end_id": get_id("Negombo Beach"),
                    "stops": [
                        {
                            "order": 1,
                            "name": "Negombo Beach",
                            "location_id": get_id("Negombo Beach"),
                        }
                    ],
                }
            ],
        },
    ]

    result = await collection.insert_many(dummy_packages)
    return {
        "message": f"Successfully seeded {len(dummy_packages)} packages",
        "inserted_ids": [str(x) for x in result.inserted_ids],
    }
