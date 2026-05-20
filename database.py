import os
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise ValueError("MONGO_URL is not defined. Add it in Render environment variables.")

client = MongoClient(MONGO_URL)

db = client["travel_tracker"]

gps_collection = db["gps_logs"]
pois_collection = db["pois"]
photos_collection = db["photos"]
