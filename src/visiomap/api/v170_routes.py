"""v1.7.0 API routes — Visitor Flow Analysis, Capacity Planning, Zone Templates."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from visiomap.database import get_db
from visiomap.repositories import LocationRepo
from visiomap.repositories.v170_repo import CapacityRepo, FlowRepo, ZoneTemplateRepo
from visiomap.schemas.v170_schemas import (
    # Flows
    FlowCreate,
    FlowResponse,
    FlowMatrixResponse,
    TopRoutesResponse,
    InboundFlowResponse,
    OutboundFlowResponse,
    # Capacity
    CapacityUpdate,
    CapacityResponse,
    CapacityOverviewResponse,
    CapacityAlertsResponse,
    # Zone Templates
    ZoneTemplateCreate,
    ZoneTemplateUpdate,
    ZoneTemplateResponse,
    ZoneTemplateDetailResponse,
    ZoneTemplateApplyResponse,
)
from visiomap.services.v170_service import (
    CapacityService,
    FlowService,
    ZoneTemplateService,
)

router = APIRouter(tags=["v1.7.0"])


# ==============================================================================
# Dependency factories
# ==============================================================================

def _flow_service(db=Depends(get_db)) -> FlowService:
    return FlowService(FlowRepo(db), LocationRepo(db))


def _capacity_service(db=Depends(get_db)) -> CapacityService:
    return CapacityService(CapacityRepo(db), LocationRepo(db))


def _template_service(db=Depends(get_db)) -> ZoneTemplateService:
    return ZoneTemplateService(ZoneTemplateRepo(db), LocationRepo(db))


# ==============================================================================
# Visitor Flow Analysis
# ==============================================================================

@router.post("/flows", response_model=FlowResponse, status_code=201)
async def create_flow(body: FlowCreate, svc: FlowService = Depends(_flow_service)):
    """Record a visitor flow between two locations."""
    if body.from_location_id == body.to_location_id:
        raise HTTPException(422, "from_location_id and to_location_id must differ")
    result = await svc.create_flow(body.model_dump())
    if not result:
        raise HTTPException(404, "One or both locations not found")
    return result


@router.get("/flows", response_model=list[FlowResponse])
async def list_flows(
    from_id: int | None = Query(None, description="Filter by origin location"),
    to_id: int | None = Query(None, description="Filter by destination location"),
    since: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    until: str | None = Query(None, description="Filter until date (YYYY-MM-DD)"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: FlowService = Depends(_flow_service),
):
    return await svc.list_flows(from_id, to_id, since, until, limit, offset)


@router.get("/analytics/flows/matrix", response_model=FlowMatrixResponse)
async def flow_matrix(svc: FlowService = Depends(_flow_service)):
    """Origin-destination matrix for all location flows."""
    return await svc.get_matrix()


@router.get("/analytics/flows/top-routes", response_model=TopRoutesResponse)
async def top_routes(
    top_n: int = Query(10, ge=1, le=100, description="Number of top routes to return"),
    svc: FlowService = Depends(_flow_service),
):
    """Top N busiest routes with average daily flow."""
    return await svc.get_top_routes(top_n)


@router.get("/locations/{location_id}/flows/inbound", response_model=InboundFlowResponse)
async def inbound_flows(
    location_id: int,
    svc: FlowService = Depends(_flow_service),
):
    """Top inbound flows to a location."""
    result = await svc.get_inbound(location_id)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.get("/locations/{location_id}/flows/outbound", response_model=OutboundFlowResponse)
async def outbound_flows(
    location_id: int,
    svc: FlowService = Depends(_flow_service),
):
    """Top outbound flows from a location."""
    result = await svc.get_outbound(location_id)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


# ==============================================================================
# Capacity Planning
# ==============================================================================

@router.patch("/locations/{location_id}/capacity", response_model=CapacityResponse)
async def set_capacity(
    location_id: int,
    body: CapacityUpdate,
    svc: CapacityService = Depends(_capacity_service),
):
    """Set max_capacity for a location."""
    result = await svc.set_capacity(location_id, body.max_capacity)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.get("/locations/{location_id}/capacity", response_model=CapacityResponse)
async def get_capacity(
    location_id: int,
    svc: CapacityService = Depends(_capacity_service),
):
    """Get capacity info for a location."""
    result = await svc.get_capacity(location_id)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.get("/analytics/capacity/overview", response_model=CapacityOverviewResponse)
async def capacity_overview(svc: CapacityService = Depends(_capacity_service)):
    """All locations with capacity set, sorted by utilization."""
    return await svc.get_overview()


@router.get("/analytics/capacity/alerts", response_model=CapacityAlertsResponse)
async def capacity_alerts(svc: CapacityService = Depends(_capacity_service)):
    """Locations approaching or exceeding capacity (>80% utilization)."""
    return await svc.get_alerts()


# ==============================================================================
# Zone Templates
# ==============================================================================

@router.post("/zone-templates", response_model=ZoneTemplateResponse, status_code=201)
async def create_template(
    body: ZoneTemplateCreate,
    svc: ZoneTemplateService = Depends(_template_service),
):
    """Create a reusable zone template."""
    return await svc.create(body.model_dump())


@router.get("/zone-templates", response_model=list[ZoneTemplateResponse])
async def list_templates(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: ZoneTemplateService = Depends(_template_service),
):
    return await svc.list_all(limit, offset)


@router.get("/zone-templates/{template_id}", response_model=ZoneTemplateDetailResponse)
async def get_template(
    template_id: int,
    svc: ZoneTemplateService = Depends(_template_service),
):
    """Get template details with count of applied locations."""
    result = await svc.get_detail(template_id)
    if not result:
        raise HTTPException(404, "Zone template not found")
    return result


@router.patch("/zone-templates/{template_id}", response_model=ZoneTemplateResponse)
async def update_template(
    template_id: int,
    body: ZoneTemplateUpdate,
    svc: ZoneTemplateService = Depends(_template_service),
):
    result = await svc.update(template_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, "Zone template not found")
    return result


@router.delete("/zone-templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    svc: ZoneTemplateService = Depends(_template_service),
):
    """Delete template (only if no locations are using it)."""
    error = await svc.delete(template_id)
    if error == "not_found":
        raise HTTPException(404, "Zone template not found")
    if error == "in_use":
        raise HTTPException(
            409,
            "Cannot delete template: locations are still using it. "
            "Remove all location associations first.",
        )


@router.post(
    "/zone-templates/{template_id}/apply/{location_id}",
    response_model=ZoneTemplateApplyResponse,
)
async def apply_template(
    template_id: int,
    location_id: int,
    svc: ZoneTemplateService = Depends(_template_service),
):
    """Apply a zone template to a location (sets category, tags, etc.)."""
    result = await svc.apply_to_location(template_id, location_id)
    if not result:
        raise HTTPException(404, "Zone template or location not found")
    return result


@router.get("/zone-templates/{template_id}/locations")
async def template_locations(
    template_id: int,
    svc: ZoneTemplateService = Depends(_template_service),
):
    """List locations using this template."""
    result = await svc.get_locations(template_id)
    if result is None:
        raise HTTPException(404, "Zone template not found")
    return result
