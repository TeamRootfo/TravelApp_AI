import logging
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)


def haversine(lat1, lon1, lat2, lon2):
    logger.info(
        f"[haversine] Calculating distance between ({lat1}, {lon1}) and ({lat2}, {lon2})"
    )
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def create_time_matrix(
    locations, speed_kmph=30, road_factor=1.25, flexible_end_index=None
):
    logger.info(
        f"[create_time_matrix] Creating time matrix for {len(locations)} locations"
    )
    size = len(locations)
    matrix = [[0] * size for _ in range(size)]

    for i in range(size):
        for j in range(size):
            if i == j:
                continue

            dist_km = haversine(
                locations[i]["latitude"],
                locations[i]["longitude"],
                locations[j]["latitude"],
                locations[j]["longitude"],
            )
            minutes = (dist_km * road_factor / speed_kmph) * 60.0
            matrix[i][j] = max(1, int(round(minutes)))

    if flexible_end_index is not None:
        for i in range(size):
            if i != flexible_end_index:
                matrix[i][flexible_end_index] = 0

    return matrix
