import logging
from typing import List, Dict, Any
from fastapi import HTTPException

from app.repositories.location_repo import LocationRepository
from app.services.intents.intent_ranker import rank_locations, rank_candidate_locations

logger = logging.getLogger(__name__)


async def get_ranked_nearby_locations_from_intention(
    *,
    repo: LocationRepository,
    intention: str,
    radius_m: int,
    limit: int,
) -> List[Dict[str, Any]]:
    logger.info(
        f"[get_ranked_nearby_locations_from_intention] intention={intention}, radius={radius_m}, limit={limit}"
    )

    allowed_tags = await repo.get_all_tags()

    # 1) Global best match = anchor
    ranked_global = await rank_locations(
        collection=repo.collection,
        intention=intention,
        allowed_tags=allowed_tags,
        weight_embedding=0.5,
        weight_tags=0.5,
        top_k=1,
    )

    if not ranked_global:
        logger.warning("[get_ranked_nearby_locations_from_intention] No global candidates found")
        return []

    anchor = ranked_global[0]
    anchor_lat = anchor.get("latitude")
    anchor_lon = anchor.get("longitude")
    anchor_id = anchor.get("_id")

    if anchor_lat is None or anchor_lon is None:
        raise HTTPException(
            status_code=500,
            detail="Best matched location has no coordinates",
        )

    # 2) Get nearby candidates
    nearby_candidates = await repo.nearby(
        anchor_id=anchor_id,
        latitude=anchor_lat,
        longitude=anchor_lon,
        max_distance_m=radius_m,
        limit=200,
    )

    if not nearby_candidates:
        logger.info("[get_ranked_nearby_locations_from_intention] No nearby candidates found")
        return []

    # 3) Rank nearby candidates
    ranked_nearby = await rank_candidate_locations(
        intention=intention,
        allowed_tags=allowed_tags,
        candidates=nearby_candidates,
        weight_embedding=0.6,
        weight_tags=0.4,
        top_k=limit,
    )

    logger.info(
        f"[get_ranked_nearby_locations_from_intention] Returning {len(ranked_nearby)} ranked nearby locations"
    )
    return ranked_nearby