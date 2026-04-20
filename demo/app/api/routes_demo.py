from fastapi import APIRouter

from app.services.demo_service import DemoService


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/scenarios")
def list_scenarios():
    return DemoService().list_scenarios()
