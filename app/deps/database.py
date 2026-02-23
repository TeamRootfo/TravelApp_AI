from app.db.mongo import get_db


def get_location_collection():
    db = get_db()
    return db["locations"]
