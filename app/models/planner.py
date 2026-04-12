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


class ReplacePlaceRequest(BaseModel):
    current_plan_places: List[str] = Field(..., description="List of location IDs currently in the plan")
    place_to_replace_id: str = Field(..., description="The ID of the place to replace")
    prompt: str = Field(..., description="The user's prompt explaining why they want to change the place or what they prefer")
    radius_m: int = Field(5000, description="The search radius for new places in meters")
    limit: int = Field(5, description="The number of alternative places to suggest")
