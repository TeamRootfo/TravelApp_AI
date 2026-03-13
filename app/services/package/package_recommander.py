import logging
from typing import List, Dict, Any
from bson import ObjectId

from app.repositories.location_repo import LocationRepository
from app.repositories.package_repo import PackageRepository
from app.services.embeddings import embed_text
from app.services.tagging import suggest_tags_from_description


logger = logging.getLogger(__name__)

THRESHOLD_VALUE = 0.6


def calculate_tag_match_score(place_tags: List[str], related_tags: List[str]) -> float:
    if not place_tags or not related_tags:
        return 0.0

    place_tags_set = {t.lower() for t in place_tags}
    related_tags_set = {t.lower() for t in related_tags}

    overlap = len(place_tags_set.intersection(related_tags_set))

    return overlap / len(related_tags_set)


async def search_relevant_locations(
    *,
    location_repo: LocationRepository,
    embeded_description: List[float],
    limit: int = 200,
) -> Dict[str, Dict[str, Any]]:
    """
    Perform vector search once and return a location score map.
    """

    pipeline = [
        {
            "$vectorSearch": {
                "index": "location_vector_index",
                "path": "embedding",
                "queryVector": embeded_description,
                "numCandidates": limit * 5,
                "limit": limit,
            }
        },
        {
            "$project": {
                "_id": 1,
                "tags": 1,
                "emb_score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = await location_repo.collection.aggregate(pipeline).to_list(length=limit)

    location_score_map = {}

    for loc in results:
        location_score_map[str(loc["_id"])] = {
            "emb_score": float(loc.get("emb_score", 0.0)),
            "tags": loc.get("tags", []),
        }

    logger.info(f"[vector search] Retrieved {len(location_score_map)} locations")

    return location_score_map


def calculate_package_score(
    *,
    package: Dict[str, Any],
    location_score_map: Dict[str, Dict[str, Any]],
    related_tags: List[str],
) -> float:

    places = package.get("places", [])

    if not places:
        return 0.0

    total_score = 0.0
    valid_places = 0

    for pid in places:

        pid_str = str(pid)

        if pid_str not in location_score_map:
            continue

        loc_data = location_score_map[pid_str]

        emb_score = loc_data["emb_score"]
        place_tags = loc_data["tags"]

        tag_score = calculate_tag_match_score(place_tags, related_tags)

        place_score = (0.7 * emb_score) + (0.3 * tag_score)

        total_score += place_score
        valid_places += 1

    if valid_places == 0:
        return 0.0

    return total_score / valid_places


async def recommended_packages(
    *,
    repo: PackageRepository,
    location_repo: LocationRepository,
    min_price: float,
    max_price: float,
    description: str,
    participant_count: int,
    limit: int = 100,
) -> List[Dict[str, Any]]:

    logger.info("[recommender] Starting package recommendation")

    embeded_description = await embed_text(description)

    allowed_tags = await location_repo.get_all_tags()
    related_tags = await suggest_tags_from_description(description, allowed_tags)

    logger.info(f"[recommender] Related tags: {related_tags}")

    filtered_packages = await repo.filtered_packages(
        min_price,
        max_price,
        participant_count,
        limit,
    )

    logger.info(f"[recommender] Packages retrieved: {len(filtered_packages)}")

    if not filtered_packages:
        return []

    location_score_map = await search_relevant_locations(
        location_repo=location_repo,
        embeded_description=embeded_description,
        limit=200,
    )

    package_scores = []

    for package in filtered_packages:

        score = calculate_package_score(
            package=package,
            location_score_map=location_score_map,
            related_tags=related_tags,
        )

        if score >= THRESHOLD_VALUE:

            package_scores.append(
                {
                    "package_id": package["id"],
                    "score": score,
                }
            )

    sorted_packages = sorted(
        package_scores,
        key=lambda x: x["score"],
        reverse=True,
    )

    logger.info(f"[recommender] Final recommended packages: {len(sorted_packages)}")

    return sorted_packages
