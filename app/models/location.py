from pydantic import BaseModel, Field
from typing import Optional, List


class LocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    latitude: float
    longitude: float
    open_time: int = Field(..., ge=0, le=1440)
    close_time: int = Field(..., ge=0, le=1440)
    visit_duration: int = Field(..., ge=0)
    description: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)


class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    open_time: Optional[int] = Field(None, ge=0, le=1440)
    close_time: Optional[int] = Field(None, ge=0, le=1440)
    visit_duration: Optional[int] = Field(None, ge=0, le=1440)
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class LocationOut(LocationBase):
    id: str
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[str] = None

