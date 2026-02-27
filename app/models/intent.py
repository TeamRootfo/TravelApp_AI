from pydantic import BaseModel, Field

class IntentNearbyRequest(BaseModel):
    intention: str = Field(..., min_length=5)
    area: str = Field(..., min_length=2)          # e.g., "Colombo"
    radius_m: int = Field(8000, ge=500, le=50000) # search radius
    limit: int = Field(10, ge=1, le=50)

class MatchOut(BaseModel):
    id: str
    name: str
    score: float