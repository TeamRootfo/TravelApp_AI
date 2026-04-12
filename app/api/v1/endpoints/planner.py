import logging
from fastapi import APIRouter, Depends, Body, HTTPException
from app.models.planner import PlannerRequest, ReplacePlaceRequest
from app.repositories.location_repo import LocationRepository
from app.deps.database import get_location_collection
from app.services.planner.multi_day import plan_trip_multi_day
from app.services.intents.intent_matcher import get_ranked_nearby_locations_from_intention
from app.services.intents.intent_ranker import rank_candidate_locations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planner", tags=["planner"])


def get_repo(collection=Depends(get_location_collection)) -> LocationRepository:
    return LocationRepository(collection)


@router.post("/plan")
async def plan_trip(
    payload: PlannerRequest = Body(...),
    repo: LocationRepository = Depends(get_repo),
):
    logger.info("[plan_trip] Planning trip from dynamic ranked nearby locations")

    ranked_locations = await get_ranked_nearby_locations_from_intention(
        repo=repo,
        intention=payload.intention,
        radius_m=payload.radius_m,
        limit=payload.limit,
    )

    if not ranked_locations:
        return {"error": "No matching nearby locations found for this intention"}

    # Add Start and End if your planner requires them
    start_location = {
        "name": "Start",
        "latitude": ranked_locations[0]["latitude"],
        "longitude": ranked_locations[0]["longitude"],
        "open_time": 0,
        "close_time": 1440,
        "visit_duration": 0,
        "score": 0,
    }

    end_location = {
        "name": "End",
        "latitude": ranked_locations[0]["latitude"],
        "longitude": ranked_locations[0]["longitude"],
        "open_time": 0,
        "close_time": 1440,
        "visit_duration": 0,
        "score": 0,
    }

    locations = [start_location] + ranked_locations + [end_location]

    try:
        result = plan_trip_multi_day(
            all_locations=locations,
            start_original_index=0,
            end_original_index=len(locations) - 1,
            start_time_minutes=8 * 60, # 8 AM
            trip_days=payload.trip_days,
            daily_time_budget_minutes=payload.daily_time_budget_minutes,
            max_stops_per_day=payload.max_stops_per_day,
        )
        logger.info("[plan_trip] Trip planned successfully")
        return result
    except Exception as e:
        logger.error(f"[plan_trip] Error planning trip: {e}")
        return {"error": str(e)}


@router.post("/replace-place")
async def replace_place(
    payload: ReplacePlaceRequest = Body(...),
    repo: LocationRepository = Depends(get_repo),
):
    logger.info(f"[replace_place] Replacing place {payload.place_to_replace_id}")
    
    place_to_replace = await repo.get(payload.place_to_replace_id)
    if not place_to_replace:
        raise HTTPException(status_code=404, detail="Place to replace not found")
        
    lat = place_to_replace.get("latitude")
    lon = place_to_replace.get("longitude")
    
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Target place has no coordinates")
        
    candidates = await repo.nearby(
        anchor_id=payload.place_to_replace_id,
        latitude=lat,
        longitude=lon,
        max_distance_m=payload.radius_m,
        limit=200,
        include_embeddings=True,
        exclude_ids=payload.current_plan_places
    )
    
    if not candidates:
        logger.info("[replace_place] No alternative candidates found nearby.")
        return []
        
    allowed_tags = await repo.get_all_tags()
    
    ranked_candidates = await rank_candidate_locations(
        intention=payload.prompt,
        allowed_tags=allowed_tags,
        candidates=candidates,
        weight_embedding=0.6,
        weight_tags=0.4,
        top_k=payload.limit
    )
    
    return ranked_candidates