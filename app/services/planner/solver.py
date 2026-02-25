from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from .distance import create_time_matrix


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