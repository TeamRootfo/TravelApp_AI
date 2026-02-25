from fastapi import FastAPI
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.v1.endpoints.locations import router as locations_router

app = FastAPI()

app.include_router(locations_router, prefix="/api/v1")



@app.on_event("startup")
async def startup():
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()