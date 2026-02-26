from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.models.planner import TagSuggestRequest
from app.repositories.location_repo import LocationRepository
from app.models.location import LocationCreate, LocationNearbyOut, LocationUpdate, LocationOut
from app.deps.database import get_location_collection
from app.services.tagging import suggest_tags_from_description

router = APIRouter(prefix="/locations", tags=["locations"])


def get_repo(collection=Depends(get_location_collection)) -> LocationRepository:
    return LocationRepository(collection)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_location(
    payload: LocationCreate,
    repo: LocationRepository = Depends(get_repo),
):
    _id = await repo.create(payload.model_dump())
    return {"id": _id}


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_locations(repo: LocationRepository = Depends(get_repo)):
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
    },
    {
        "name": "Temple A",
        "latitude": 6.9200,
        "longitude": 79.8700,
        "open_time": 540,
        "close_time": 1020,
        "visit_duration": 60,
        "description": "A serene Buddhist temple adorned with intricate carvings and incense-filled halls. A peaceful retreat from the city’s rush, perfect for quiet reflection and cultural discovery.",
        "tags": ["temple", "culture", "spiritual", "peaceful", "architecture", "heritage", "religious-site"],
    },
    {
        "name": "Museum B",
        "latitude": 6.9100,
        "longitude": 79.8800,
        "open_time": 600,
        "close_time": 1200,
        "visit_duration": 45,
        "description": "A thoughtfully curated museum showcasing Sri Lanka’s rich history, artifacts, and artistic heritage. Ideal for history lovers and curious minds.",
        "tags": ["museum", "history", "education", "culture", "artifacts", "indoor", "learning"],
    },
    {
        "name": "National Library",
        "latitude": 6.9210,
        "longitude": 79.8670,
        "open_time": 540,
        "close_time": 1080,
        "visit_duration": 30,
        "description": "A calm and intellectual space filled with archives, literature, and research materials. A quiet escape for book lovers and deep thinkers.",
        "tags": ["library", "quiet", "study", "books", "intellectual", "indoor", "relaxed"],
    },
    {
        "name": "Galle Face Green",
        "latitude": 6.9270,
        "longitude": 79.8428,
        "open_time": 0,
        "close_time": 1440,
        "visit_duration": 30,
        "description": "A breezy oceanfront promenade perfect for sunset strolls, kite flying, and tasting local street food while waves crash nearby.",
        "tags": ["park", "sea", "sunset", "street-food", "relaxed", "outdoor", "family-friendly", "scenic"],
    },
    {
        "name": "Independence Square",
        "latitude": 6.9036,
        "longitude": 79.8693,
        "open_time": 480,
        "close_time": 1080,
        "visit_duration": 40,
        "description": "A historic national monument surrounded by lush gardens and jogging paths. Popular among locals for morning walks and evening relaxation.",
        "tags": ["monument", "park", "history", "architecture", "photography", "outdoor", "cultural-landmark"],
    },
    {
        "name": "Old Parliament",
        "latitude": 6.9335,
        "longitude": 79.8486,
        "open_time": 540,
        "close_time": 1020,
        "visit_duration": 35,
        "description": "An elegant colonial-era building overlooking the sea, offering stunning architecture and historical significance.",
        "tags": ["history", "architecture", "colonial", "photography", "heritage-site", "scenic"],
    },
    {
        "name": "Beira Lake",
        "latitude": 6.9279,
        "longitude": 79.8559,
        "open_time": 480,
        "close_time": 1200,
        "visit_duration": 50,
        "description": "A tranquil lake in the middle of the city with walking paths, small temples, and scenic views — perfect for a calm afternoon break.",
        "tags": ["lake", "nature", "relaxing", "scenic", "photography", "outdoor", "peaceful"],
    },
    {
        "name": "Pettah Market",
        "latitude": 6.9352,
        "longitude": 79.8501,
        "open_time": 480,
        "close_time": 1140,
        "visit_duration": 45,
        "description": "A chaotic and colorful bazaar packed with vendors selling spices, textiles, electronics, and street snacks — a true sensory adventure.",
        "tags": ["market", "shopping", "street-life", "local-experience", "budget-friendly", "food", "vibrant"],
    },
    {
        "name": "Kelaniya Temple",
        "latitude": 6.9490,
        "longitude": 79.9187,
        "open_time": 480,
        "close_time": 1080,
        "visit_duration": 60,
        "description": "One of Sri Lanka’s most sacred Buddhist temples, known for its grand murals and spiritual atmosphere.",
        "tags": ["temple", "religion", "spiritual", "heritage", "pilgrimage", "architecture", "cultural-site"],
    },
    {
        "name": "Negombo Beach",
        "latitude": 7.2086,
        "longitude": 79.8358,
        "open_time": 480,
        "close_time": 1200,
        "visit_duration": 90,
        "description": "Golden sands stretching along the coastline with fishing boats dotting the horizon — ideal for sunset views and relaxed beach vibes.",
        "tags": ["beach", "sea", "sunset", "relaxing", "romantic", "nature", "coastal", "photography"],
    },
    {
        "name": "Gangaramaya Temple",
        "latitude": 6.9167,
        "longitude": 79.8562,
        "open_time": 540,
        "close_time": 1080,
        "visit_duration": 50,
    
        "description": "A fascinating temple blending Sri Lankan, Thai, and Chinese architectural styles with a museum-like collection of artifacts.",
        "tags": ["temple", "culture", "architecture", "museum-like", "spiritual", "photography", "heritage"],
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
    }
    ]

    inserted_ids: list[str] = []
    for loc in locations:
        inserted_ids.append(await repo.create(loc))

    return {"inserted_ids": inserted_ids}


@router.post("/tags/suggest", response_model=dict)
async def suggest_tags(
    payload: TagSuggestRequest,
    repo: LocationRepository = Depends(get_repo),
):
    allowed_tags = await repo.get_all_tags()
    try:
            
        tags = await suggest_tags_from_description(
            description=payload.description,
            allowed_tags=allowed_tags,
        )
        return {"tags": tags}
    except Exception as e:
        print(f"Error suggesting tags: {e}")
        raise HTTPException(status_code=500, detail="Failed to suggest tags")

@router.get("/", response_model=list[LocationOut])
async def list_locations(
    limit: int = Query(200, ge=1, le=500),
    include_deleted: bool = Query(False),
    repo: LocationRepository = Depends(get_repo),
):
    return await repo.list_all(limit=limit, include_deleted=include_deleted)

@router.get("/nearby", response_model=list[LocationNearbyOut])
async def get_nearby_locations(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    max_distance_m: int = Query(5000, ge=1, le=200000),
    limit: int = Query(20, ge=1, le=100),
    repo: LocationRepository = Depends(get_repo),
    
):
    print(f"Received nearby request: lat={latitude}, lon={longitude}, max_distance_m={max_distance_m}, limit={limit}")
    return await repo.nearby(
        latitude=latitude,
        longitude=longitude,
        max_distance_m=max_distance_m,
        limit=limit
    )
    
@router.get("/{location_id}", response_model=LocationOut)
async def get_location(
    location_id: str,
    include_deleted: bool = Query(False),
    repo: LocationRepository = Depends(get_repo),
):
    doc = await repo.get(location_id, include_deleted=include_deleted)
    if not doc:
        raise HTTPException(status_code=404, detail="Location not found")
    return doc


@router.patch("/{location_id}")
async def update_location(
    location_id: str,
    payload: LocationUpdate,
    repo: LocationRepository = Depends(get_repo),
):
    ok = await repo.update(location_id, payload.model_dump(exclude_unset=True))
    if not ok:
        raise HTTPException(status_code=404, detail="Location not found or no fields updated")
    return {"updated": True}



@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: str,
    repo: LocationRepository = Depends(get_repo),
):
    ok = await repo.soft_delete(location_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Location not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

