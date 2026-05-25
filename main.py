from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional
import os
from datetime import datetime

app = FastAPI(title="SmartTrip API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URI = os.environ.get("MONGO_URL", "")
client = MongoClient(MONGODB_URI)
db = client["smarttrip"]

class LocationModel(BaseModel):
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: Optional[float] = 0.0
    accuracy: Optional[float] = 0.0

class BatteryModel(BaseModel):
    level: int = 100
    charging: bool = False

class GpsDataModel(BaseModel):
    user_id: str
    trip_id: str
    trip_name: Optional[str] = ""
    location: LocationModel
    battery: Optional[BatteryModel] = None
    recorded_at: Optional[str] = None

class PoiModel(BaseModel):
    user_id: str
    trip_id: str
    trip_name: Optional[str] = ""
    name: str
    type: str
    location: LocationModel
    rating: int = 0
    comment: Optional[str] = ""
    recorded_at: Optional[str] = None
    photo_base64: Optional[str] = None

class PhotoModel(BaseModel):
    user_id: str
    trip_id: str
    trip_name: Optional[str] = ""
    location: LocationModel
    photo_base64: str
    recorded_at: Optional[str] = None

@app.get("/")
def root():
    return {"status": "SmartTrip API running", "version": "1.0"}

@app.post("/gps")
def save_gps(data: GpsDataModel):
    doc = data.dict()
    doc["received_at"] = datetime.utcnow().isoformat()
    result = db["gps_logs"].insert_one(doc)
    return {"status": "ok", "id": str(result.inserted_id)}

@app.get("/gps/{user_id}")
def get_gps(user_id: str):
    return list(db["gps_logs"].find({"user_id": user_id}, {"_id": 0}))

@app.post("/poi")
def save_poi(data: PoiModel):
    doc = data.dict()
    doc["received_at"] = datetime.utcnow().isoformat()
    result = db["pois"].insert_one(doc)
    return {"status": "ok", "id": str(result.inserted_id)}

@app.get("/poi/{user_id}")
def get_pois(user_id: str):
    return list(db["pois"].find({"user_id": user_id}, {"_id": 0}))

@app.post("/photo")
def save_photo(data: PhotoModel):
    doc = data.dict()
    doc["received_at"] = datetime.utcnow().isoformat()
    result = db["photos"].insert_one(doc)
    return {"status": "ok", "id": str(result.inserted_id)}

@app.get("/photos/{user_id}")
def get_photos(user_id: str):
    return list(db["photos"].find({"user_id": user_id}, {"_id": 0}))

@app.get("/trip/{trip_id}")
def get_trip(trip_id: str):
    gps    = list(db["gps_logs"].find({"trip_id": trip_id}, {"_id": 0}))
    pois   = list(db["pois"].find({"trip_id": trip_id}, {"_id": 0}))
    photos = list(db["photos"].find({"trip_id": trip_id}, {"_id": 0}))
    if not gps and not pois and not photos:
        raise HTTPException(status_code=404, detail="Voyage introuvable")
    trip_name = ""
    if gps: trip_name = gps[0].get("trip_name", "")
    elif pois: trip_name = pois[0].get("trip_name", "")
    return {
        "trip_id":     trip_id,
        "trip_name":   trip_name,
        "gps_count":   len(gps),
        "poi_count":   len(pois),
        "photo_count": len(photos),
        "pois":        pois,
        "photos":      [{"location": p["location"], "recorded_at": p.get("recorded_at")} for p in photos]
    }

@app.delete("/trip/{trip_id}")
def delete_trip(trip_id: str):
    r1 = db["gps_logs"].delete_many({"trip_id": trip_id})
    r2 = db["pois"].delete_many({"trip_id": trip_id})
    r3 = db["photos"].delete_many({"trip_id": trip_id})
    return {
        "status":        "deleted",
        "gps_deleted":   r1.deleted_count,
        "poi_deleted":   r2.deleted_count,
        "photo_deleted": r3.deleted_count
    }
