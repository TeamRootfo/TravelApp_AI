from pydantic import BaseModel, Field
from typing import List


class PlannerRequest(BaseModel):
    name: str
    latitude: float
    longitude: float
    open_time: int
    close_time: int
    visit_duration: int
    score: int
    start_index: int

class TagSuggestRequest(BaseModel):
    description: str = Field(..., min_length=5)