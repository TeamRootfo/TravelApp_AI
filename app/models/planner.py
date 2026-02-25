from pydantic import BaseModel
from typing import List


class PlannerRequest(BaseModel):
    start_index: int
    end_index: int
    start_time_minutes: int
    trip_days: int = 2
    daily_time_budget_minutes: int = 600
    max_stops_per_day: int = 3