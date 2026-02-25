from fastapi import APIRouter
from app.models.planner import PlannerRequest
from app.services.planner.multi_day import plan_trip_multi_day_carry_end_forward

router = APIRouter(prefix="/planner", tags=["planner"])


@router.post("/plan")
async def plan_trip():
    locations = [...]  # load from DB later

    result = plan_trip_multi_day_carry_end_forward(
        all_locations=locations,
        start_original_index=0,
        end_original_index=len(locations) - 1,
        start_time_minutes=8 * 60,
        trip_days=3,
        daily_time_budget_minutes=600,
        max_stops_per_day=3,
    )
    return result