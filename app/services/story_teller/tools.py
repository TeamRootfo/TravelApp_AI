# app/services/wiki_tool.py
import httpx
from typing import Dict, Any
from urllib.parse import quote

WIKI_UA = "TravelApp_AI/1.0 (contact: gptemail404@gmail.com)"

async def fetch_wikipedia_summary(place: str) -> Dict[str, Any]:
    """Fetch a short factual summary for a place from Wikipedia."""
    place = (place or "").strip()
    if not place:
        return {"status": "error", "error_message": "place is empty"}

    # URL encode the title (spaces, symbols)
    title = quote(place)

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    headers = {
        "User-Agent": WIKI_UA,
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            r = await client.get(url)

        if r.status_code != 200:
            return {
                "status": "error",
                "error_message": f"Wikipedia lookup failed (HTTP {r.status_code}). Try a more specific name.",
            }

        data = r.json()
        
        return {
            "status": "success",
            "title": data.get("title"),
            "summary": data.get("extract"),
            "url": (data.get("content_urls") or {}).get("desktop", {}).get("page"),
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Request failed: {e}"}