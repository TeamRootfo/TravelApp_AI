from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Stop(BaseModel):
    order: int
    name: str
    location_id: str

class PackageState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DEACTIVE = "deactive"
    
class Day(BaseModel):
    day: int
    is_last_day: bool
    start_name: str
    start_id: str
    end_name: str
    end_id: str
    stops: List[Stop]


class Package(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    number_of_days: int
    price: float
    rating: int
    max_number_of_participants: int
    owner_id: str
    owner: str
    places: List[str]
    states: PackageState
    days: List[Day]
    is_deleted: bool
    createdAt: datetime
    updatedAt: datetime

class PackageRecommandRequest(BaseModel):
    min_price: float = Field(..., ge=0)
    max_price: float = Field(..., ge=0)
    description: str
    participant_count: int = Field(..., ge=1)
    limit: int = Field(100, ge=1, le=100)
    