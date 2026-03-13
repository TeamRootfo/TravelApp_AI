import logging
from fastapi import FastAPI
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.v1.endpoints.locations import router as locations_router
from app.api.v1.endpoints.package import router as package_router
from app.api.v1.endpoints.planner import router as planner_router
from app.api.v1.endpoints.tts import router as tts_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.include_router(locations_router, prefix="/api/v1")
app.include_router(package_router, prefix="/api/v1")
app.include_router(planner_router, prefix="/api/v1")
app.include_router(tts_router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    logger.info("[startup] Starting up the application")
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown():
    logger.info("[shutdown] Shutting down the application")
    await close_mongo_connection()
