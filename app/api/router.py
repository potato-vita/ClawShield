from fastapi import APIRouter

from app.api.v1 import audits, dashboard, events, graph, health, opencaw_bridge, rules, runs, system, tasks, ui

router = APIRouter(prefix="/v1")

router.include_router(health.router, tags=["health"])
router.include_router(system.router, tags=["system"])
router.include_router(tasks.router, tags=["tasks"])
router.include_router(runs.router, tags=["runs"])
router.include_router(events.router, tags=["events"])
router.include_router(graph.router, tags=["graph"])
router.include_router(audits.router, tags=["audits"])
router.include_router(dashboard.router, tags=["dashboard"])
router.include_router(rules.router, tags=["rules"])
router.include_router(opencaw_bridge.router, tags=["bridge"])
router.include_router(ui.router, tags=["ui"])
