import logging
from copy import deepcopy
from .solver import solve_one_day

logger = logging.getLogger(__name__)


def plan_trip_multi_day(
    all_locations,
    start_original_index,
    end_original_index,
    start_time_minutes,
    trip_days=2,
    daily_time_budget_minutes=300,
    max_wait_time=60,
    speed_kmph=30,
    road_factor=1.25,
    score_to_minutes=2,
    minimize_travel_weight=1,
    time_limit_seconds=5,
    max_stops_per_day=6,
):
    logger.info(
        f"[plan_trip_multi_day] Planning multi-day trip for {trip_days} days and {len(all_locations)} POIs"
    )
    remaining_original = [
        i
        for i in range(len(all_locations))
        if i not in (start_original_index, end_original_index)
    ]

    current_start_original = start_original_index
    day_results = []
    total_score = 0

    def build_day_output(
        day_label,
        is_last_day,
        res,
        day_original_indices,
        start_original,
        next_start_original=None,
    ):
        logger.info(f"[build_day_output] Building output for day: {day_label}")
        """
        Convert OR-Tools result to API-friendly JSON.
        """
        mapping = day_original_indices
        route_nodes = res["route_nodes"]
        arrival_times = res["arrival_times"]
        travel_to_next = res["travel_to_next"]

        stops = []
        # route_nodes includes final depot at the end; travel_to_next aligns with route_nodes[:-1]
        for i, day_node in enumerate(route_nodes[:-1]):
            orig_idx = mapping[day_node]
            loc = all_locations[orig_idx]
            stops.append(
                {
                    "order": i,
                    "original_index": orig_idx,
                    "name": loc.get("name"),
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                    "arrival_time_minutes": arrival_times[i],
                    "visit_duration": loc.get("visit_duration", 0),
                    "score": loc.get("score", 0),
                    "travel_to_next_minutes": travel_to_next[i],
                }
            )

        # Final arrival time at depot (EOD or real End)
        end_time = arrival_times[-1]
        end_day_node = route_nodes[-1]
        end_orig_idx = mapping[end_day_node] if end_day_node < len(mapping) else None

        if is_last_day and end_orig_idx is not None:
            end_loc = all_locations[end_orig_idx]
            stops.append(
                {
                    "order": len(stops),
                    "original_index": end_orig_idx,
                    "name": end_loc.get("name"),
                    "latitude": end_loc.get("latitude"),
                    "longitude": end_loc.get("longitude"),
                    "arrival_time_minutes": end_time,
                    "visit_duration": end_loc.get("visit_duration", 0),
                    "score": end_loc.get("score", 0),
                    "travel_to_next_minutes": 0,
                }
            )

        visited_original = []
        for day_node in res["visited_optional"]:
            visited_original.append(mapping[day_node])

        return {
            "day": day_label,
            "is_last_day": is_last_day,
            "start_original_index": start_original,
            "start_name": all_locations[start_original].get("name"),
            "next_start_original_index": next_start_original,
            "total_score_day": res["total_score"],
            "end_time_minutes": end_time,
            "end_name": (
                all_locations[end_original_index].get("name")
                if is_last_day
                else (
                    all_locations[next_start_original].get("name")
                    if next_start_original is not None
                    else None
                )
            ),
            "visited_original_indices": visited_original,
            "stops": stops,
        }

    def run_final_to_end_day(start_from_original):
        logger.info(
            f"[run_final_to_end_day] Planning final stretch from {start_from_original}"
        )
        """One last day: go from current start to real End (no optional POIs)."""
        day_original_indices = [start_from_original, end_original_index]
        day_locations = [deepcopy(all_locations[i]) for i in day_original_indices]

        # start node is just a starting point
        day_locations[0]["score"] = 0
        day_locations[0]["visit_duration"] = 0
        day_locations[0]["open_time"] = 0
        day_locations[0]["close_time"] = 1440

        res = solve_one_day(
            day_locations=day_locations,
            start_index=0,
            end_index=1,
            start_time_minutes=start_time_minutes,
            daily_time_budget_minutes=daily_time_budget_minutes,
            max_wait_time=max_wait_time,
            speed_kmph=speed_kmph,
            road_factor=road_factor,
            score_to_minutes=score_to_minutes,
            minimize_travel_weight=minimize_travel_weight,
            time_limit_seconds=time_limit_seconds,
            flexible_end_index=None,
            max_stops_per_day=max_stops_per_day,
        )
        if res is None:
            return None

        return build_day_output(
            day_label="FINAL",
            is_last_day=True,
            res=res,
            day_original_indices=day_original_indices,
            start_original=start_from_original,
            next_start_original=None,
        )

    for day in range(1, trip_days + 1):
        is_last_day = day == trip_days

        # If nothing left to visit, stop early.
        # If not last day, still go to End on a final day.
        if not remaining_original:
            if not is_last_day:
                final_plan = run_final_to_end_day(current_start_original)
                if final_plan:
                    day_results.append(final_plan)
            break

        day_original_indices = [current_start_original] + remaining_original

        if is_last_day:
            day_original_indices.append(end_original_index)
            day_locations = [deepcopy(all_locations[i]) for i in day_original_indices]
            day_end_index = len(day_locations) - 1
            flexible_end_index = None
        else:
            # EOD node: same coordinates as current start (dummy depot)
            eod_node = {
                "name": "EOD",
                "latitude": all_locations[current_start_original]["latitude"],
                "longitude": all_locations[current_start_original]["longitude"],
                "open_time": 0,
                "close_time": 1440,
                "visit_duration": 0,
                "score": 0,
            }
            day_locations = [
                deepcopy(all_locations[i]) for i in day_original_indices
            ] + [eod_node]
            day_end_index = len(day_locations) - 1
            flexible_end_index = day_end_index

        # Start node is just starting point
        day_locations[0]["score"] = 0
        day_locations[0]["visit_duration"] = 0
        day_locations[0]["open_time"] = 0
        day_locations[0]["close_time"] = 1440

        res = solve_one_day(
            day_locations=day_locations,
            start_index=0,
            end_index=day_end_index,
            start_time_minutes=start_time_minutes,
            daily_time_budget_minutes=daily_time_budget_minutes,
            max_wait_time=max_wait_time,
            speed_kmph=speed_kmph,
            road_factor=road_factor,
            score_to_minutes=score_to_minutes,
            minimize_travel_weight=minimize_travel_weight,
            time_limit_seconds=time_limit_seconds,
            flexible_end_index=flexible_end_index,
            max_stops_per_day=max_stops_per_day,
        )

        if res is None:
            day_results.append(
                {
                    "day": day,
                    "is_last_day": is_last_day,
                    "error": "No solution",
                }
            )
            continue

        total_score += res["total_score"]

        # Convert visited (day indices) -> original indices
        visited_original = [day_original_indices[dn] for dn in res["visited_optional"]]
        visited_set = set(visited_original)
        remaining_original = [i for i in remaining_original if i not in visited_set]

        # Next start = last REAL stop before depot
        route_nodes = res["route_nodes"]
        if len(route_nodes) >= 2:
            last_real_day_node = route_nodes[-2]
            if last_real_day_node == 0:
                next_start_original = current_start_original
            else:
                next_start_original = day_original_indices[last_real_day_node]
        else:
            next_start_original = current_start_original

        day_results.append(
            build_day_output(
                day_label=day,
                is_last_day=is_last_day,
                res=res,
                day_original_indices=(
                    day_original_indices
                    if is_last_day
                    else (day_original_indices + [None])
                ),  # placeholder for EOD mapping slot
                start_original=current_start_original,
                next_start_original=None if is_last_day else next_start_original,
            )
        )

        current_start_original = next_start_original

    logger.info(
        f"[plan_trip_multi_day] Completed multi-day plan. Total score: {total_score}"
    )
    return {
        "start_original_index": start_original_index,
        "end_original_index": end_original_index,
        "trip_days_requested": trip_days,
        "daily_time_budget_minutes": daily_time_budget_minutes,
        "max_stops_per_day": max_stops_per_day,
        "total_score": total_score,
        "days": day_results,
        "unvisited_original_indices": remaining_original,
    }
