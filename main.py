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

# Important : tes anciens voyages sont dans cette base.
db = client["travel_tracker"]


class LocationModel(BaseModel):
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: Optional[float] = 0.0
    accuracy: Optional[float] = 0.0


class BatteryModel(BaseModel):
    level: int = 100
    charging: Optional[bool] = False
    is_charging: Optional[bool] = False


class GpsDataModel(BaseModel):
    user_id: str
    trip_id: str
    trip_name: Optional[str] = ""
    location: LocationModel
    battery: Optional[BatteryModel] = None
    recorded_at: Optional[str] = None


class PoiModel(BaseModel):
    poi_id: Optional[str] = None
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

    # null = photo libre sur la carte
    # "poi_..." = photo souvenir liée à un POI précis
    linked_poi_id: Optional[str] = None


@app.get("/")
def root():
    return {
        "status": "SmartTrip API running",
        "version": "1.1",
        "database": "travel_tracker"
    }


@app.post("/gps")
def save_gps(data: GpsDataModel):
    doc = data.dict()
    doc["received_at"] = datetime.utcnow().isoformat()

    result = db["gps_logs"].insert_one(doc)

    return {
        "status": "ok",
        "id": str(result.inserted_id)
    }


@app.get("/gps/{user_id}")
def get_gps(user_id: str):
    return list(
        db["gps_logs"].find(
            {"user_id": user_id},
            {"_id": 0}
        )
    )


@app.post("/poi")
def save_poi(data: PoiModel):
    doc = data.dict()

    if not doc.get("poi_id"):
        doc["poi_id"] = "poi_" + str(int(datetime.utcnow().timestamp() * 1000))

    doc["received_at"] = datetime.utcnow().isoformat()

    result = db["pois"].insert_one(doc)

    return {
        "status": "ok",
        "id": str(result.inserted_id),
        "poi_id": doc["poi_id"]
    }


@app.get("/poi/{user_id}")
def get_pois(user_id: str):
    return list(
        db["pois"].find(
            {"user_id": user_id},
            {"_id": 0}
        )
    )


@app.post("/photo")
def save_photo(data: PhotoModel):
    doc = data.dict()
    doc["received_at"] = datetime.utcnow().isoformat()

    result = db["photos"].insert_one(doc)

    return {
        "status": "ok",
        "id": str(result.inserted_id),
        "linked_poi_id": doc.get("linked_poi_id")
    }


@app.get("/photos/{user_id}")
def get_photos(user_id: str):
    return list(
        db["photos"].find(
            {"user_id": user_id},
            {"_id": 0}
        )
    )


@app.get("/trip/{trip_id}")
def get_trip(trip_id: str):
    gps = list(
        db["gps_logs"].find(
            {"trip_id": trip_id},
            {"_id": 0}
        )
    )

    pois = list(
        db["pois"].find(
            {"trip_id": trip_id},
            {"_id": 0}
        )
    )

    photos = list(
        db["photos"].find(
            {"trip_id": trip_id},
            {"_id": 0}
        )
    )

    if not gps and not pois and not photos:
        raise HTTPException(status_code=404, detail="Voyage introuvable")

    trip_name = ""

    if gps:
        trip_name = gps[0].get("trip_name", "")
    elif pois:
        trip_name = pois[0].get("trip_name", "")
    elif photos:
        trip_name = photos[0].get("trip_name", "")

    return {
        "trip_id": trip_id,
        "trip_name": trip_name,
        "gps_count": len(gps),
        "poi_count": len(pois),
        "photo_count": len(photos),
        "gps": gps,
        "pois": pois,
        "photos": photos
    }


@app.get("/trips/{user_id}")
def get_trips(user_id: str):
    gps_docs = list(
        db["gps_logs"].find(
            {"user_id": user_id},
            {"_id": 0}
        )
    )

    poi_docs = list(
        db["pois"].find(
            {"user_id": user_id},
            {"_id": 0}
        )
    )

    photo_docs = list(
        db["photos"].find(
            {"user_id": user_id},
            {"_id": 0}
        )
    )

    trips = {}

    def ensure_trip(doc):
        trip_id = doc.get("trip_id", "trip_unknown")

        if trip_id not in trips:
            trips[trip_id] = {
                "trip_id": trip_id,
                "trip_name": doc.get("trip_name", ""),
                "gps_count": 0,
                "poi_count": 0,
                "photo_count": 0,
                "first_recorded_at": doc.get("recorded_at"),
                "last_recorded_at": doc.get("recorded_at")
            }

        recorded_at = doc.get("recorded_at")

        if recorded_at:
            current_first = trips[trip_id].get("first_recorded_at")
            current_last = trips[trip_id].get("last_recorded_at")

            if current_first is None or recorded_at < current_first:
                trips[trip_id]["first_recorded_at"] = recorded_at

            if current_last is None or recorded_at > current_last:
                trips[trip_id]["last_recorded_at"] = recorded_at

        if not trips[trip_id].get("trip_name") and doc.get("trip_name"):
            trips[trip_id]["trip_name"] = doc.get("trip_name")

        return trip_id

    for doc in gps_docs:
        trip_id = ensure_trip(doc)
        trips[trip_id]["gps_count"] += 1

    for doc in poi_docs:
        trip_id = ensure_trip(doc)
        trips[trip_id]["poi_count"] += 1

    for doc in photo_docs:
        trip_id = ensure_trip(doc)
        trips[trip_id]["photo_count"] += 1

    return list(trips.values())


@app.delete("/trip/{trip_id}")
def delete_trip(trip_id: str):
    r1 = db["gps_logs"].delete_many({"trip_id": trip_id})
    r2 = db["pois"].delete_many({"trip_id": trip_id})
    r3 = db["photos"].delete_many({"trip_id": trip_id})

    return {
        "status": "deleted",
        "gps_deleted": r1.deleted_count,
        "poi_deleted": r2.deleted_count,
        "photo_deleted": r3.deleted_count
    }


@app.get("/debug/counts")
def debug_counts():
    return {
        "database": "travel_tracker",
        "gps_logs_count": db["gps_logs"].count_documents({}),
        "gps_logs_amin_count": db["gps_logs"].count_documents({"user_id": "amin"}),
        "pois_count": db["pois"].count_documents({}),
        "pois_amin_count": db["pois"].count_documents({"user_id": "amin"}),
        "photos_count": db["photos"].count_documents({}),
        "photos_amin_count": db["photos"].count_documents({"user_id": "amin"}),
        "linked_photos_count": db["photos"].count_documents(
            {"linked_poi_id": {"$ne": None}}
        ),
        "free_photos_count": db["photos"].count_documents(
            {"linked_poi_id": None}
        )
    }
