from pydantic import BaseModel, Field


class IntentAutoAreaRequest(BaseModel):
    intention: str = Field(..., min_length=5)
    radius_m: int = Field(15000, ge=500, le=50000)
    limit: int = Field(10, ge=1, le=50)
    prefilter: int = Field(300, ge=50, le=2000)


class MatchOut(BaseModel):
    name: str
    latitude: float
    longitude: float
    open_time: int
    close_time: int
    visit_duration: int
    score: float
