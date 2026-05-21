from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from database import gps_collection, pois_collection, photos_collection
from schemas import GPSData, Location

app = FastAPI(title="SmartTrip API")

# CORS — autorise les requêtes depuis n'importe quelle origine
# (nécessaire pour le partage de liens publics)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "SmartTrip API — opérationnelle"}


# ─────────────────────────────────────────────────────────────────────────────
# GPS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/gps")
def receive_gps(data: GPSData):
    if data.battery.level <= 15:
        raise HTTPException(status_code=400, detail="Battery too low")
    document = data.model_dump()
    document["received_at"] = datetime.utcnow().isoformat()
    result = gps_collection.insert_one(document)
    return {"status": "ok", "inserted_id": str(result.inserted_id)}


@app.get("/gps")
def get_all_gps():
    return list(gps_collection.find({}, {"_id": 0}))


@app.get("/gps/{user_id}")
def get_user_gps(user_id: str):
    return list(gps_collection.find({"user_id": user_id}, {"_id": 0}))


# ─────────────────────────────────────────────────────────────────────────────
# POI
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/pois")
def receive_poi(data: PoiData):
    document = data.model_dump()
    document["received_at"] = datetime.utcnow().isoformat()
    result = pois_collection.insert_one(document)
    return {"status": "ok", "inserted_id": str(result.inserted_id)}


@app.get("/pois")
def get_all_pois():
    return list(pois_collection.find({}, {"_id": 0}))


@app.get("/pois/{user_id}")
def get_user_pois(user_id: str):
    return list(pois_collection.find({"user_id": user_id}, {"_id": 0}))


# ─────────────────────────────────────────────────────────────────────────────
# Photos
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/photos")
def receive_photo(data: PhotoData):
    document = data.model_dump()
    document["received_at"] = datetime.utcnow().isoformat()
    result = photos_collection.insert_one(document)
    return {"status": "ok", "inserted_id": str(result.inserted_id)}


@app.get("/photos")
def get_all_photos():
    return list(photos_collection.find({}, {"_id": 0}))


@app.get("/photos/{user_id}")
def get_user_photos(user_id: str):
    return list(photos_collection.find({"user_id": user_id}, {"_id": 0}))


# ─────────────────────────────────────────────────────────────────────────────
# Partage public d'un voyage — QR code
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/trip/{trip_id}")
def get_trip_public(trip_id: str):
    """
    Endpoint public — retourne toutes les données d'un voyage :
    points GPS, POI et photos, sans authentification.

    Utilisé pour générer le lien de partage et le QR code dans l'app Android.
    URL du QR : https://smarttrip-api.onrender.com/trip/{trip_id}

    Les données photo_base64 volumineuses sont retournées tronquées
    (les 50 premiers caractères) pour un affichage web léger.
    L'app Android récupère les photos complètes via /photos/{user_id}.
    """
    # GPS — on exclut _id MongoDB non sérialisable
    gps_points = list(gps_collection.find({"trip_id": trip_id}, {"_id": 0}))

    if not gps_points:
        raise HTTPException(status_code=404, detail=f"Voyage '{trip_id}' introuvable")

    # POI — on tronque photo_base64 pour la réponse publique
    pois = list(pois_collection.find({"trip_id": trip_id}, {"_id": 0}))
    for poi in pois:
        if poi.get("photo_base64"):
            poi["photo_base64"] = poi["photo_base64"][:50] + "...[tronqué]"

    # Photos — on tronque aussi
    photos = list(photos_collection.find({"trip_id": trip_id}, {"_id": 0}))
    for photo in photos:
        if photo.get("photo_base64"):
            photo["photo_base64"] = photo["photo_base64"][:50] + "...[tronqué]"

    # Infos résumé du voyage
    trip_name = gps_points[0].get("trip_name", trip_id) if gps_points else trip_id

    return {
        "trip_id":    trip_id,
        "trip_name":  trip_name,
        "nb_gps":     len(gps_points),
        "nb_pois":    len(pois),
        "nb_photos":  len(photos),
        "gps_points": gps_points,
        "pois":       pois,
        "photos":     photos,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Suppression
# ─────────────────────────────────────────────────────────────────────────────

@app.delete("/trips/{trip_id}")
def delete_trip(trip_id: str):
    gps_deleted    = gps_collection.delete_many({"trip_id": trip_id}).deleted_count
    pois_deleted   = pois_collection.delete_many({"trip_id": trip_id}).deleted_count
    photos_deleted = photos_collection.delete_many({"trip_id": trip_id}).deleted_count
    return {
        "deleted_gps":    gps_deleted,
        "deleted_pois":   pois_deleted,
        "deleted_photos": photos_deleted,
    }


@app.delete("/gps/all")
def delete_all_gps():
    return {"deleted": gps_collection.delete_many({}).deleted_count}


@app.delete("/pois/all")
def delete_all_pois():
    return {"deleted": pois_collection.delete_many({}).deleted_count}


@app.delete("/photos/all")
def delete_all_photos():
    return {"deleted": photos_collection.delete_many({}).deleted_count}
