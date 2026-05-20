from fastapi import FastAPI, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from database import gps_collection, pois_collection, photos_collection
from schemas import GPSData, Location

app = FastAPI(title="Travel Tracker API")


class PoiData(BaseModel):
    user_id: str
    trip_id: str
    trip_name: str = ""
    name: str
    type: str
    location: Location
    rating: int
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


@app.get("/")
def root():
    return {"message": "L'API est lancée !"}


@app.post("/gps")
def receive_gps(data: GPSData):
    if data.battery.level <= 15:
        raise HTTPException(status_code=400, detail="Battery too low")

    document = data.model_dump()
    document["received_at"] = datetime.utcnow().isoformat()

    result = gps_collection.insert_one(document)

    return {
        "status": "ok",
        "inserted_id": str(result.inserted_id)
    }


@app.get("/gps")
def get_all_gps():
    data = list(gps_collection.find({}, {"_id": 0}))
    return data


@app.get("/gps/{user_id}")
def get_user_gps(user_id: str):
    data = list(gps_collection.find({"user_id": user_id}, {"_id": 0}))
    return data


@app.post("/pois")
def receive_poi(data: PoiData):
    document = data.model_dump()
    document["received_at"] = datetime.utcnow().isoformat()

    result = pois_collection.insert_one(document)

    return {
        "status": "ok",
        "inserted_id": str(result.inserted_id)
    }


@app.get("/pois")
def get_all_pois():
    pois = list(pois_collection.find({}, {"_id": 0}))
    return pois


@app.get("/pois/{user_id}")
def get_user_pois(user_id: str):
    pois = list(pois_collection.find({"user_id": user_id}, {"_id": 0}))
    return pois


@app.post("/photos")
def receive_photo(data: PhotoData):
    document = data.model_dump()
    document["received_at"] = datetime.utcnow().isoformat()

    result = photos_collection.insert_one(document)

    return {
        "status": "ok",
        "inserted_id": str(result.inserted_id)
    }


@app.get("/photos")
def get_all_photos():
    photos = list(photos_collection.find({}, {"_id": 0}))
    return photos


@app.get("/photos/{user_id}")
def get_user_photos(user_id: str):
    photos = list(photos_collection.find({"user_id": user_id}, {"_id": 0}))
    return photos


@app.delete("/trips/{trip_id}")
def delete_trip(trip_id: str):
    gps_deleted = gps_collection.delete_many({"trip_id": trip_id}).deleted_count
    pois_deleted = pois_collection.delete_many({"trip_id": trip_id}).deleted_count
    photos_deleted = photos_collection.delete_many({"trip_id": trip_id}).deleted_count

    return {
        "deleted_gps": gps_deleted,
        "deleted_pois": pois_deleted,
        "deleted_photos": photos_deleted
    }


@app.delete("/gps/all")
def delete_all_gps():
    deleted = gps_collection.delete_many({}).deleted_count
    return {"deleted": deleted}


@app.delete("/pois/all")
def delete_all_pois():
    deleted = pois_collection.delete_many({}).deleted_count
    return {"deleted": deleted}


@app.delete("/photos/all")
def delete_all_photos():
    deleted = photos_collection.delete_many({}).deleted_count
    return {"deleted": deleted}
