from typing import List, Dict, Any
import math

from app.services.embeddings import embed_text
from app.services.tagging import suggest_tags_from_description
from app.models.planner import PlannerRequest


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
    # normalize cosine from [-1, 1] -> [0, 1]
    return (cosine(a, b) + 1.0) / 2.0


def tag_overlap_score(intent_tags: List[str], place_tags: List[str]) -> float:
    it = [t.strip().lower() for t in (intent_tags or []) if t and t.strip()]
    pt = {t.strip().lower() for t in (place_tags or []) if t and t.strip()}

    if not it:
        return 0.0  # no tag signal, rely on embedding only
    matched = sum(1 for t in it if t in pt)
    return matched / len(it)


async def rank_locations(
    intention: str,
    allowed_tags: List[str],
    candidates: List[Dict[str, Any]],
    weight_embedding: float = 0.8,
    weight_tags: float = 0.2,
    top_k: int = 10,
) -> List[Dict[str, Any]]:

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

        final = (weight_embedding * emb_score) + (weight_tags * t_score)

        results.append(
            {
                "name": loc.get("name"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "open_time": loc.get("open_time"),
                "close_time": loc.get("close_time"),
                "visit_duration": loc.get("visit_duration"),
                "score": float(final),
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_k]
