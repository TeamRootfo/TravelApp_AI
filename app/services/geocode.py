import logging
import httpx
from typing import Optional, Tuple

from starlette import status

from starlette import status
from app.core.config import settings

logger = logging.getLogger(__name__)


async def geocode_area(area: str) -> Optional[Tuple[float, float]]:
    logger.info(f"[geocode_area] Geocoding area: {area}")
    if not area or not area.strip():
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"

    params = {
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    try:

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data["status"] != "OK":
            logger.error(
                f"[geocode_area] Google geocode failed: {data['status']} {data.get('error_message')}"
            )
            return None

        location = data["results"][0]["geometry"]["location"]

        lat = location["lat"]
        lon = location["lng"]

        logger.info(f"[geocode_area] Successfully geocoded {area} to {lat}, {lon}")
        return lat, lon
    except Exception as e:
        logger.error(f"[geocode_area] Geocoding error for area '{area}': {e}")
        return None
