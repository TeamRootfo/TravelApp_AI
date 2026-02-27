import httpx
from typing import Optional, Tuple

from starlette import status

from starlette import status
from app.core.config import settings


async def geocode_area(area: str) -> Optional[Tuple[float, float]]:
    if not area or not area.strip():
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"

    params = {
        "address": area,
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    print(f"Geocoding area: '{area}' with Google Maps API...")
    try:

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data["status"] != "OK":
            print("Google geocode failed:", data["status"], data.get("error_message"))
            return None

        location = data["results"][0]["geometry"]["location"]

        lat = location["lat"]
        lon = location["lng"]

        return lat, lon
    except Exception as e:
        print(f"Geocoding error for area '{area}': {e}")
        return None
