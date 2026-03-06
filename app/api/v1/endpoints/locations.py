import logging
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status

from app.models.intent import IntentAutoAreaRequest, MatchOut
from app.models.planner import PlannerRequest
from app.models.planner import TagSuggestRequest
from app.repositories.location_repo import LocationRepository
from app.models.location import (
    LocationCreate,
    LocationNearbyOut,
    LocationUpdate,
    LocationOut,
)
from app.deps.database import get_location_collection
from app.services.geocode import geocode_area
from app.services.intent_ranker import rank_locations, rank_candidate_locations
from app.services.tagging import suggest_tags_from_description

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["locations"])


def get_repo(collection=Depends(get_location_collection)) -> LocationRepository:
    logger.info("[get_repo] Getting LocationRepository instance")
    return LocationRepository(collection)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_location(
    payload: LocationCreate,
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(f"[create_location] Creating location: {payload.name}")
    _id = await repo.create(payload.model_dump())
    logger.info(f"[create_location] Created location with ID: {_id}")
    return {"id": _id}


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_locations(repo: LocationRepository = Depends(get_repo)):
    logger.info("[seed_locations] Seeding locations")
    # Must include all required fields from LocationBase (description is required).
    locations = [
        {
            "name": "Start",
            "latitude": 6.9271,
            "longitude": 79.8612,
            "open_time": 0,
            "close_time": 1440,
            "visit_duration": 0,
            "description": "The vibrant heart of Colombo where your journey begins — surrounded by colonial architecture, busy streets, and the pulse of the city waking up.",
            "tags": ["start", "city-center", "urban", "landmark", "orientation-point"],
            "rating": 0.0,
        },
        {
            "name": "Temple A",
            "latitude": 6.9200,
            "longitude": 79.8700,
            "open_time": 540,
            "close_time": 1020,
            "visit_duration": 60,
            "description": "A serene Buddhist temple adorned with intricate carvings and incense-filled halls. A peaceful retreat from the city’s rush, perfect for quiet reflection and cultural discovery.",
            "tags": [
                "temple",
                "culture",
                "spiritual",
                "peaceful",
                "architecture",
                "heritage",
                "religious-site",
            ],
            "rating": 4.5,
        },
        {
            "name": "Museum B",
            "latitude": 6.9100,
            "longitude": 79.8800,
            "open_time": 600,
            "close_time": 1200,
            "visit_duration": 45,
            "description": "A thoughtfully curated museum showcasing Sri Lanka’s rich history, artifacts, and artistic heritage. Ideal for history lovers and curious minds.",
            "tags": [
                "museum",
                "history",
                "education",
                "culture",
                "artifacts",
                "indoor",
                "learning",
            ],
            "rating": 4.0,
        },
        {
            "name": "National Library",
            "latitude": 6.9210,
            "longitude": 79.8670,
            "open_time": 540,
            "close_time": 1080,
            "visit_duration": 30,
            "description": "A calm and intellectual space filled with archives, literature, and research materials. A quiet escape for book lovers and deep thinkers.",
            "tags": [
                "library",
                "quiet",
                "study",
                "books",
                "intellectual",
                "indoor",
                "relaxed",
            ],
            "rating": 4.0,
        },
        {
            "name": "Galle Face Green",
            "latitude": 6.9270,
            "longitude": 79.8428,
            "open_time": 0,
            "close_time": 1440,
            "visit_duration": 30,
            "description": "A breezy oceanfront promenade perfect for sunset strolls, kite flying, and tasting local street food while waves crash nearby.",
            "tags": [
                "park",
                "sea",
                "sunset",
                "street-food",
                "relaxed",
                "outdoor",
                "family-friendly",
                "scenic",
            ],
            "rating": 3.0,
        },
        {
            "name": "Independence Square",
            "latitude": 6.9036,
            "longitude": 79.8693,
            "open_time": 480,
            "close_time": 1080,
            "visit_duration": 40,
            "description": "A historic national monument surrounded by lush gardens and jogging paths. Popular among locals for morning walks and evening relaxation.",
            "tags": [
                "monument",
                "park",
                "history",
                "architecture",
                "photography",
                "outdoor",
                "cultural-landmark",
            ],
        },
        {
            "name": "Old Parliament",
            "latitude": 6.9335,
            "longitude": 79.8486,
            "open_time": 540,
            "close_time": 1020,
            "visit_duration": 35,
            "description": "An elegant colonial-era building overlooking the sea, offering stunning architecture and historical significance.",
            "tags": [
                "history",
                "architecture",
                "colonial",
                "photography",
                "heritage-site",
                "scenic",
            ],
            "rating": 4.0,
        },
        {
            "name": "Beira Lake",
            "latitude": 6.9279,
            "longitude": 79.8559,
            "open_time": 480,
            "close_time": 1200,
            "visit_duration": 50,
            "description": "A tranquil lake in the middle of the city with walking paths, small temples, and scenic views — perfect for a calm afternoon break.",
            "tags": [
                "lake",
                "nature",
                "relaxing",
                "scenic",
                "photography",
                "outdoor",
                "peaceful",
            ],
            "rating": 2.0,
        },
        {
            "name": "Pettah Market",
            "latitude": 6.9352,
            "longitude": 79.8501,
            "open_time": 480,
            "close_time": 1140,
            "visit_duration": 45,
            "description": "A chaotic and colorful bazaar packed with vendors selling spices, textiles, electronics, and street snacks — a true sensory adventure.",
            "tags": [
                "market",
                "shopping",
                "street-life",
                "local-experience",
                "budget-friendly",
                "food",
                "vibrant",
            ],
            "rating": 2.0,
        },
        {
            "name": "Kelaniya Temple",
            "latitude": 6.9490,
            "longitude": 79.9187,
            "open_time": 480,
            "close_time": 1080,
            "visit_duration": 60,
            "description": "One of Sri Lanka’s most sacred Buddhist temples, known for its grand murals and spiritual atmosphere.",
            "tags": [
                "temple",
                "religion",
                "spiritual",
                "heritage",
                "pilgrimage",
                "architecture",
                "cultural-site",
            ],
            "rating": 2.0,
        },
        {
            "name": "Negombo Beach",
            "latitude": 7.2086,
            "longitude": 79.8358,
            "open_time": 480,
            "close_time": 1200,
            "visit_duration": 90,
            "description": "Golden sands stretching along the coastline with fishing boats dotting the horizon — ideal for sunset views and relaxed beach vibes.",
            "tags": [
                "beach",
                "sea",
                "sunset",
                "relaxing",
                "romantic",
                "nature",
                "coastal",
                "photography",
            ],
            "rating": 5.0,
        },
        {
            "name": "Gangaramaya Temple",
            "latitude": 6.9167,
            "longitude": 79.8562,
            "open_time": 540,
            "close_time": 1080,
            "visit_duration": 50,
            "description": "A fascinating temple blending Sri Lankan, Thai, and Chinese architectural styles with a museum-like collection of artifacts.",
            "tags": [
                "temple",
                "culture",
                "architecture",
                "museum-like",
                "spiritual",
                "photography",
                "heritage",
            ],
            "rating": 5.0,
        },
        {
            "name": "End",
            "latitude": 7.2080,
            "longitude": 79.8350,
            "open_time": 0,
            "close_time": 1440,
            "visit_duration": 0,
            "description": "The final stop of your journey — a peaceful coastal spot to unwind, reflect, and enjoy the sunset after a day of exploration.",
            "tags": ["end", "coastal", "relaxation", "sunset", "reflection-point"],
            "rating": 0.0,
        },
    ]

    inserted_ids: list[str] = []
    for loc in locations:
        inserted_ids.append(await repo.create(loc))

    logger.info(f"[seed_locations] Successfully seeded {len(inserted_ids)} locations")
    return {"inserted_ids": inserted_ids}


@router.post("/tags/suggest", response_model=dict)
async def suggest_tags(
    payload: TagSuggestRequest,
    repo: LocationRepository = Depends(get_repo),
):
    allowed_tags = await repo.get_all_tags()
    try:
        logger.info(
            f"[suggest_tags] Suggesting tags for description: {payload.description[:50]}..."
        )
        tags = await suggest_tags_from_description(
            description=payload.description,
            allowed_tags=allowed_tags,
        )
        logger.info(f"[suggest_tags] Suggested tags: {tags}")
        return {"tags": tags}
    except Exception as e:
        logger.error(f"[suggest_tags] Error suggesting tags: {e}")
        raise HTTPException(status_code=500, detail="Failed to suggest tags")


@router.get("/", response_model=list[LocationOut])
async def list_locations(
    limit: int = Query(200, ge=1, le=500),
    include_deleted: bool = Query(False),
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(
        f"[list_locations] Listing locations: limit={limit}, include_deleted={include_deleted}"
    )
    return await repo.list_all(limit=limit, include_deleted=include_deleted)


@router.post("/intent/auto-nearby-match", response_model=list[MatchOut])
async def intent_auto_nearby_match(
    payload: IntentAutoAreaRequest = Body(...),
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(f"[intent_auto_nearby_match] Intention: {payload.intention}")
    allowed_tags = await repo.get_all_tags()

    # 1) Global ranking to find anchor location
    global_candidates = await repo.fetch_for_ranking(limit=payload.prefilter)
    if not global_candidates:
        return []

    ranked_global = await rank_locations(
        collection=repo.collection,
        intention=payload.intention,
        allowed_tags=allowed_tags,
        weight_embedding=0.5,
        weight_tags=0.5,
        top_k=1,  # we only need the best anchor
    )

    logger.info(f"[intent_auto_nearby_match] ranked global candidates: {ranked_global}")

    if not ranked_global:
        logger.warning("[intent_auto_nearby_match] No global candidates found")
        return []

    anchor = ranked_global[0]
    logger.info(f"[intent_auto_nearby_match] Anchor found: {anchor}")
    anchor_lat = anchor.get("latitude")
    anchor_lon = anchor.get("longitude")

    if anchor_lat is None or anchor_lon is None:
        raise HTTPException(
            status_code=500, detail="Best matched location has no coordinates"
        )

    # Optional safety: if anchor score is too low, don’t trust it
    # if anchor["score"] < 0.35:
    #     raise HTTPException(status_code=400, detail="Could not confidently determine an area from your intention.")

    # 2) Nearby candidates around anchor
    nearby_candidates = await repo.nearby(
        anchor_id=anchor.get("_id"),
        latitude=anchor_lat,
        longitude=anchor_lon,
        max_distance_m=payload.radius_m,
        limit=200,
    )
    logger.info(
        f"[intent_auto_nearby_match] Nearby candidates count: {len(nearby_candidates)}"
    )

    if not nearby_candidates:
        return []

    # 3) Rerank nearby results by intention (semantic+tags)
    ranked_nearby = await rank_candidate_locations(
        intention=payload.intention,
        allowed_tags=allowed_tags,
        candidates=nearby_candidates,
        weight_embedding=0.6,
        weight_tags=0.4,
        top_k=payload.limit,
    )

    logger.info(f"[intent_auto_nearby_match] Ranked nearby count: {len(ranked_nearby)}")

    return ranked_nearby


@router.get("/nearby", response_model=list[LocationNearbyOut])
async def get_nearby_locations(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    max_distance_m: int = Query(5000, ge=1, le=200000),
    limit: int = Query(20, ge=1, le=100),
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(
        f"[get_nearby_locations] lat={latitude}, lon={longitude}, max_distance_m={max_distance_m}, limit={limit}"
    )
    return await repo.nearby(
        latitude=latitude,
        longitude=longitude,
        max_distance_m=max_distance_m,
        limit=limit,
    )


@router.get("/{location_id}", response_model=LocationOut)
async def get_location(
    location_id: str,
    include_deleted: bool = Query(False),
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(f"[get_location] Fetching location ID: {location_id}")
    doc = await repo.get(location_id, include_deleted=include_deleted)
    if not doc:
        logger.warning(f"[get_location] Location not found: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")
    return doc


@router.patch("/{location_id}")
async def update_location(
    location_id: str,
    payload: LocationUpdate,
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(f"[update_location] Updating location ID: {location_id}")
    ok = await repo.update(location_id, payload.model_dump(exclude_unset=True))
    if not ok:
        logger.warning(f"[update_location] Failed to update location ID: {location_id}")
        raise HTTPException(
            status_code=404, detail="Location not found or no fields updated"
        )
    logger.info(f"[update_location] Successfully updated location ID: {location_id}")
    return {"updated": True}


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: str,
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(f"[delete_location] Deleting location ID: {location_id}")
    ok = await repo.soft_delete(location_id)
    if not ok:
        logger.warning(f"[delete_location] Failed to delete location ID: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")
    logger.info(f"[delete_location] Successfully deleted location ID: {location_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
