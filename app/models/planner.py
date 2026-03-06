from pydantic import BaseModel, Field
from typing import List


class PlannerRequest(BaseModel):
    intention: str
    radius_m: int = 5000
    limit: int = 10
    trip_days: int = 3
    daily_time_budget_minutes: int = 600
    max_stops_per_day: int = 3


class TagSuggestRequest(BaseModel):
    description: str = Field(..., min_length=5)
