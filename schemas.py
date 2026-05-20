from pydantic import BaseModel, Field
from typing import Optional


class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None


class Battery(BaseModel):
    level: int = Field(..., ge=0, le=100)
    is_charging: bool


class GPSData(BaseModel):
    user_id: str
    trip_id: Optional[str] = None
    trip_name: Optional[str] = ""
    location: Location
    battery: Battery
    recorded_at: str


class PoiData(BaseModel):
    user_id: str
    trip_id: str
    trip_name: Optional[str] = ""
    name: str
    type: str
    location: Location
    rating: int = Field(..., ge=0, le=5)
    comment: str
    recorded_at: str
    photo_base64: Optional[str] = None


class PhotoData(BaseModel):
    user_id: str
    trip_id: str
    trip_name: Optional[str] = ""
    location: Location
    photo_base64: str
    recorded_at: str
