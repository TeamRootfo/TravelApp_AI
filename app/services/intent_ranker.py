import logging
import math
from typing import List, Dict, Any, Optional

from app.services.embeddings import embed_text
from app.services.tagging import suggest_tags_from_description

logger = logging.getLogger(__name__)


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def cosine_0_1(a: List[float], b: List[float]) -> float:
    return (cosine(a, b) + 1.0) / 2.0


def tag_overlap_score(intent_tags: List[str], place_tags: List[str]) -> float:
    it = [t.strip().lower() for t in (intent_tags or []) if t and t.strip()]
    pt = {t.strip().lower() for t in (place_tags or []) if t and t.strip()}
    if not it:
        return 0.0
    matched = sum(1 for t in it if t in pt)
    return matched / len(it)


def normalize_rating(rating: float, max_rating: float = 5.0) -> float:
    if rating is None:
        return 0.0
    r = float(rating)
    if r < 0.0:
        r = 0.0
    if r > max_rating:
        r = max_rating
    return r / max_rating


async def rank_locations(
    *,
    collection,
    intention: str,
    allowed_tags: List[str],
    weight_embedding: float = 0.8,
    weight_tags: float = 0.2,
    top_k: int = 10,
    num_candidates: int = 200,
    embedding_path: str = "embedding",
    prefilter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Global ranking using MongoDB Atlas Vector Search.
    """
    logger.info(f"[rank_locations] Global vector ranking for intention={intention!r}")

    intent_vec = await embed_text(intention)
    intent_tags = await suggest_tags_from_description(
        description=intention,
        allowed_tags=allowed_tags,
    )

    pipeline: List[Dict[str, Any]] = [
        {
            "$vectorSearch": {
                "index": "location_vector_index",
                "path": embedding_path,
                "queryVector": intent_vec,
                "numCandidates": num_candidates,
                "limit": max(top_k * 10, top_k),
                **({"filter": prefilter} if prefilter else {}),
            }
        },
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "latitude": 1,
                "longitude": 1,
                "open_time": 1,
                "close_time": 1,
                "visit_duration": 1,
                "tags": 1,
                "rating": 1,
                "emb_score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    raw = await collection.aggregate(pipeline).to_list(length=max(top_k * 10, top_k))
    logger.info(f"[rank_locations] Raw candidates: {raw}")

    results: List[Dict[str, Any]] = []
    for loc in raw:
        emb_score = float(loc.get("emb_score") or 0.0)
        t_score = tag_overlap_score(intent_tags, loc.get("tags") or [])
        r_score = normalize_rating(loc.get("rating") or 0.0)

        final = (weight_embedding * emb_score) + (weight_tags * t_score) + r_score

        results.append(
            {
                "_id": loc.get("_id"),
                "name": loc.get("name"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "open_time": loc.get("open_time"),
                "close_time": loc.get("close_time"),
                "visit_duration": loc.get("visit_duration"),
                "score": float(final),
                "emb_score": emb_score,
                "tag_score": t_score,
                "rating_score": r_score,
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


async def rank_candidate_locations(
    *,
    intention: str,
    allowed_tags: List[str],
    candidates: List[Dict[str, Any]],
    weight_embedding: float = 0.8,
    weight_tags: float = 0.2,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    In-memory ranking for an already selected candidate list, such as nearby places.
    """
    logger.info(
        f"[rank_candidate_locations] Ranking {len(candidates)} nearby candidates"
    )

    intent_vec = await embed_text(intention)
    intent_tags = await suggest_tags_from_description(
        description=intention,
        allowed_tags=allowed_tags,
    )

    results: List[Dict[str, Any]] = []
    for loc in candidates:
        loc_vec = loc.get("embedding") or []
        emb_score = cosine_0_1(intent_vec, loc_vec)
        t_score = tag_overlap_score(intent_tags, loc.get("tags") or [])
        r_score = normalize_rating(loc.get("rating") or 0.0)

        final = (weight_embedding * emb_score) + (weight_tags * t_score) + r_score

        results.append(
            {
                "_id": loc.get("_id"),
                "name": loc.get("name"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "open_time": loc.get("open_time"),
                "close_time": loc.get("close_time"),
                "visit_duration": loc.get("visit_duration"),
                "score": float(final),
                "emb_score": emb_score,
                "tag_score": t_score,
                "rating_score": r_score,
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
