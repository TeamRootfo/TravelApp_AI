from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from math import radians, sin, cos, sqrt, atan2
from copy import deepcopy


# --------------------------
# Haversine distance (km)
# --------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def fmt_hhmm(minutes_in_day: int) -> str:
    h = minutes_in_day // 60
    m = minutes_in_day % 60
    return f"{h:02d}:{m:02d}"


def create_time_matrix(locations, speed_kmph=30, road_factor=1.25, flexible_end_index=None):
    """
    Travel time matrix in minutes.
    - Rounds and enforces minimum 1 minute (except i==j).
    - If flexible_end_index is provided, travel TO that node is forced to 0 from any node,
      enabling "end anywhere" behavior for intermediate days.
    """
    size = len(locations)
    matrix = [[0] * size for _ in range(size)]

    for i in range(size):
        for j in range(size):
            if i == j:
                matrix[i][j] = 0
                continue

            dist_km = haversine(
                locations[i]["latitude"], locations[i]["longitude"],
                locations[j]["latitude"], locations[j]["longitude"],
            )
            minutes = (dist_km * road_factor / speed_kmph) * 60.0
            matrix[i][j] = max(1, int(round(minutes)))

    if flexible_end_index is not None:
        for i in range(size):
            if i != flexible_end_index:
                matrix[i][flexible_end_index] = 0

    return matrix


# --------------------------
# Solve ONE day
# --------------------------
def solve_one_day(
    day_locations,
    start_index,
    end_index,
    start_time_minutes,
    daily_time_budget_minutes=300,
    max_wait_time=60,
    speed_kmph=30,
    road_factor=1.25,
    score_to_minutes=2,
    minimize_travel_weight=1,
    time_limit_seconds=5,
    flexible_end_index=None,
    max_stops_per_day=None,   # <-- NEW
):
    """
    Single-day solver:
      - objective: minimize travel_cost + skipped_penalties
      - feasibility: time windows + service durations + waiting + daily budget
      - NEW: optional max_stops_per_day (counts POIs visited; excludes start/end/EOD)
    """
    time_matrix = create_time_matrix(
        day_locations,
        speed_kmph=speed_kmph,
        road_factor=road_factor,
        flexible_end_index=flexible_end_index,
    )
    n = len(day_locations)

    manager = pywrapcp.RoutingIndexManager(n, 1, [start_index], [end_index])
    routing = pywrapcp.RoutingModel(manager)

    # Objective: travel cost only
    def travel_cost_cb(from_i, to_i):
        a = manager.IndexToNode(from_i)
        b = manager.IndexToNode(to_i)
        return time_matrix[a][b] * minimize_travel_weight

    travel_cost_idx = routing.RegisterTransitCallback(travel_cost_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(travel_cost_idx)

    # Time dimension: travel + service at destination
    def time_transit_cb(from_i, to_i):
        a = manager.IndexToNode(from_i)
        b = manager.IndexToNode(to_i)
        travel = time_matrix[a][b]
        service = int(day_locations[b].get("visit_duration", 0))
        return travel + service

    time_transit_idx = routing.RegisterTransitCallback(time_transit_cb)

    max_end_time = start_time_minutes + daily_time_budget_minutes
    routing.AddDimension(
        time_transit_idx,
        max_wait_time,
        max_end_time,
        False,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Time windows
    for node, loc in enumerate(day_locations):
        idx = manager.NodeToIndex(node)
        if node == start_index:
            time_dim.CumulVar(idx).SetRange(start_time_minutes, start_time_minutes)
        elif node == end_index:
            pass
        else:
            open_t = int(loc.get("open_time", 0))
            close_t = int(loc.get("close_time", 1440))
            time_dim.CumulVar(idx).SetRange(open_t, close_t)

    # Optional nodes with penalties (score -> minutes)
    for node, loc in enumerate(day_locations):
        if node in (start_index, end_index):
            continue
        score = int(loc.get("score", 0))
        penalty = max(0, score * score_to_minutes)
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    # --------------------------
    # NEW: Max stops/day dimension
    # --------------------------
    if max_stops_per_day is not None:
        # Count "POI stops" by charging 1 when the destination is a real POI.
        # Excludes: start_index, end_index (real End or EOD), and also excludes the day start node.
        def stop_count_cb(from_i, to_i):
            to_node = manager.IndexToNode(to_i)
            if to_node in (start_index, end_index):
                return 0
            return 1

        stop_cb_idx = routing.RegisterTransitCallback(stop_count_cb)
        routing.AddDimension(
            stop_cb_idx,
            0,                   # no slack
            int(max_stops_per_day),
            True,                # start cumul = 0
            "Stops",
        )

    # Search
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = int(time_limit_seconds)

    sol = routing.SolveWithParameters(params)
    if not sol:
        return None

    # Extract route
    route_nodes = []
    arrival_times = []
    travel_to_next = []

    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        t = sol.Value(time_dim.CumulVar(index))
        route_nodes.append(node)
        arrival_times.append(t)

        nxt = sol.Value(routing.NextVar(index))
        nxt_node = manager.IndexToNode(nxt)
        travel_to_next.append(time_matrix[node][nxt_node])

        index = nxt

    end_node = manager.IndexToNode(index)
    end_time = sol.Value(time_dim.CumulVar(index))

    # Score collected + visited POIs (exclude start/end)
    total_score = 0
    visited_optional = []
    for node in route_nodes:
        if node not in (start_index, end_index):
            total_score += int(day_locations[node].get("score", 0))
            visited_optional.append(node)

    return {
        "route_nodes": route_nodes + [end_node],
        "arrival_times": arrival_times + [end_time],
        "travel_to_next": travel_to_next,
        "visited_optional": visited_optional,
        "total_score": total_score,
        "end_time": end_time,
    }


# --------------------------
# Multi-day (carry start forward + final End only last day) + max stops/day
# --------------------------
def plan_trip_multi_day_carry_end_forward(
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
    max_stops_per_day=6,   # <-- NEW
):
    remaining_original = [
        i for i in range(len(all_locations))
        if i not in (start_original_index, end_original_index)
    ]

    current_start_original = start_original_index

    day_plans = []
    total_score = 0

    def run_final_to_end_day(start_from_original):
        """One last day: go from current start to real End, no POIs."""
        day_original_indices = [start_from_original, end_original_index]
        day_locations = [deepcopy(all_locations[i]) for i in day_original_indices]
        # Make sure start has no service/score
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
        return {
            "day": "FINAL",
            "is_last_day": True,
            "result": res,
            "day_original_indices": day_original_indices,
            "start_original": start_from_original,
        }

    for day in range(1, trip_days + 1):
        is_last_day = (day == trip_days)

        # If nothing left to visit, stop early.
        # If not last day, we still add one FINAL day to reach End, then break.
        if not remaining_original:
            if not is_last_day:
                final_plan = run_final_to_end_day(current_start_original)
                if final_plan["result"] is not None:
                    day_plans.append(final_plan)
            break

        day_original_indices = [current_start_original] + remaining_original

        if is_last_day:
            day_original_indices.append(end_original_index)
            day_locations = [deepcopy(all_locations[i]) for i in day_original_indices]
            day_end_index = len(day_locations) - 1
            flexible_end_index = None
        else:
            eod_node = {
                "name": "EOD",
                "latitude": all_locations[current_start_original]["latitude"],
                "longitude": all_locations[current_start_original]["longitude"],
                "open_time": 0,
                "close_time": 1440,
                "visit_duration": 0,
                "score": 0,
            }
            day_locations = [deepcopy(all_locations[i]) for i in day_original_indices] + [eod_node]
            day_end_index = len(day_locations) - 1
            flexible_end_index = day_end_index

        # Start node is just a starting point (not a "visit")
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
            max_stops_per_day=max_stops_per_day,  # <-- NEW
        )

        if res is None:
            day_plans.append({"day": day, "error": "No solution"})
            continue

        total_score += res["total_score"]

        # Convert visited (day indices) -> original indices
        visited_original = []
        for day_node in res["visited_optional"]:
            # visited_optional never includes end depot (EOD/End), so safe
            visited_original.append(day_original_indices[day_node])

        visited_set = set(visited_original)
        remaining_original = [i for i in remaining_original if i not in visited_set]

        # Next start = last REAL stop before end depot
        route_nodes = res["route_nodes"]
        if len(route_nodes) >= 2:
            last_real_day_node = route_nodes[-2]
            if last_real_day_node == 0:
                next_start_original = current_start_original
            else:
                next_start_original = day_original_indices[last_real_day_node]
        else:
            next_start_original = current_start_original

        day_plans.append({
            "day": day,
            "is_last_day": is_last_day,
            "result": res,
            "day_original_indices": day_original_indices,
            "start_original": current_start_original,
            "next_start_original": next_start_original,
            "visited_original": visited_original,
        })

        current_start_original = next_start_original

    # --------------------------
    # Print
    # --------------------------
    print("\n==============================")
    print("=== Multi-Day Trip Plan (A+ + max stops/day) ===")
    print("==============================")
    print("Rule: Day N starts at Day N-1 last stop; real End only on last day.")
    print(f"Max stops/day: {max_stops_per_day}\n")

    print(f"Start time each day: {fmt_hhmm(start_time_minutes)}")
    print(f"Daily budget: {daily_time_budget_minutes} min ({daily_time_budget_minutes/60:.1f} hrs)")
    print(f"Days planned: {trip_days}")
    print(f"Speed: {speed_kmph} km/h | road_factor={road_factor} | Wait allowed: {max_wait_time} min")
    print(f"Objective: maximize score vs travel (score_to_minutes={score_to_minutes}, travel_weight={minimize_travel_weight})")

    for dp in day_plans:
        day = dp["day"]
        if "error" in dp:
            print(f"\n--- Day {day} ---\n{dp['error']}")
            continue

        res = dp["result"]
        mapping = dp["day_original_indices"]

        print(f"\n--- Day {day} ---")
        print(f"Start at: {all_locations[dp['start_original']]['name']}")

        route_nodes = res["route_nodes"]
        arrival = res["arrival_times"]
        travel_next = res["travel_to_next"]

        # Print all except the final depot
        for i, day_node in enumerate(route_nodes[:-1]):
            orig = mapping[day_node]
            name = all_locations[orig]["name"]
            t = arrival[i]
            print(f"{i:02d}. {name:<22} arrive {fmt_hhmm(t)} ({t} min)")
            print(f"    -> travel to next: {travel_next[i]} min")

        end_time = arrival[-1]
        if dp.get("is_last_day", False) and day != "FINAL":
            print(f"End at (FINAL): {all_locations[end_original_index]['name']} at {fmt_hhmm(end_time)} ({end_time} min)")
        elif day == "FINAL":
            print(f"End at (FINAL): {all_locations[end_original_index]['name']} at {fmt_hhmm(end_time)} ({end_time} min)")
        else:
            last_real_node = route_nodes[-2]
            last_real_orig = mapping[last_real_node]
            print(f"End-of-day at: {all_locations[last_real_orig]['name']} at {fmt_hhmm(end_time)} ({end_time} min)")
            print(f"Next day starts at: {all_locations[dp['next_start_original']]['name']}")

        print(f"Day score collected: {res['total_score']}")
        print(f"Day elapsed: {end_time - start_time_minutes} min")

    print(f"\nTOTAL score across days: {total_score}")

    if remaining_original:
        print("\nUnvisited places after planning:")
        for i in remaining_original:
            print(f" - {all_locations[i]['name']} (score={all_locations[i].get('score', 0)})")
    else:
        print("\nAll places visited (within constraints).")


# --------------------------
# Example
# --------------------------
if __name__ == "__main__":
    locations = [
        {"name": "Start", "latitude": 6.9271, "longitude": 79.8612, "open_time": 0, "close_time": 1440, "visit_duration": 0, "score": 0},

        {"name": "Temple A", "latitude": 6.9200, "longitude": 79.8700, "open_time": 540, "close_time": 1020, "visit_duration": 60, "score": 100},
        {"name": "Museum B", "latitude": 6.9100, "longitude": 79.8800, "open_time": 600, "close_time": 1200, "visit_duration": 45, "score": 80},
        {"name": "National Library", "latitude": 6.9210, "longitude": 79.8670, "open_time": 540, "close_time": 1080, "visit_duration": 30, "score": 70},
        {"name": "Galle Face Green", "latitude": 6.9270, "longitude": 79.8428, "open_time": 0, "close_time": 1440, "visit_duration": 30, "score": 60},
        {"name": "Independence Square", "latitude": 6.9036, "longitude": 79.8693, "open_time": 480, "close_time": 1080, "visit_duration": 40, "score": 75},
        {"name": "Old Parliament", "latitude": 6.9335, "longitude": 79.8486, "open_time": 540, "close_time": 1020, "visit_duration": 35, "score": 65},
        {"name": "Beira Lake", "latitude": 6.9279, "longitude": 79.8559, "open_time": 480, "close_time": 1200, "visit_duration": 50, "score": 85},
        {"name": "Pettah Market", "latitude": 6.9352, "longitude": 79.8501, "open_time": 480, "close_time": 1140, "visit_duration": 45, "score": 90},
        {"name": "Kelaniya Temple", "latitude": 6.9490, "longitude": 79.9187, "open_time": 480, "close_time": 1080, "visit_duration": 60, "score": 95},
        {"name": "Negombo Beach", "latitude": 7.2086, "longitude": 79.8358, "open_time": 480, "close_time": 1200, "visit_duration": 90, "score": 90},
        {"name": "Gangaramaya Temple", "latitude": 6.9167, "longitude": 79.8562, "open_time": 540, "close_time": 1080, "visit_duration": 50, "score": 85},

        {"name": "End", "latitude": 7.2080, "longitude": 79.8350, "open_time": 0, "close_time": 1440, "visit_duration": 0, "score": 0},
    ]

    plan_trip_multi_day_carry_end_forward(
        all_locations=locations,
        start_original_index=0,
        end_original_index=len(locations) - 1,
        start_time_minutes=8 * 60,
        trip_days=3,
        daily_time_budget_minutes=600,
        max_wait_time=60,
        speed_kmph=35,
        road_factor=1.25,
        score_to_minutes=2,
        minimize_travel_weight=1,
        time_limit_seconds=5,
        max_stops_per_day=3,   # <--- set this!
    )