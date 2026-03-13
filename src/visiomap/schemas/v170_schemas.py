"""v1.7.0 schemas — Visitor Flow Analysis, Capacity Planning, Zone Templates."""
from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    # Visitor Flow Analysis
    "FlowCreate",
    "FlowResponse",
    "FlowMatrixCell",
    "FlowMatrixResponse",
    "TopRouteEntry",
    "TopRoutesResponse",
    "InboundFlowEntry",
    "InboundFlowResponse",
    "OutboundFlowEntry",
    "OutboundFlowResponse",
    # Capacity Planning
    "CapacityUpdate",
    "CapacityResponse",
    "CapacityOverviewEntry",
    "CapacityOverviewResponse",
    "CapacityAlertEntry",
    "CapacityAlertsResponse",
    # Zone Templates
    "ZoneTemplateCreate",
    "ZoneTemplateUpdate",
    "ZoneTemplateResponse",
    "ZoneTemplateDetailResponse",
    "ZoneTemplateApplyResponse",
]


# -- Visitor Flow Analysis -----------------------------------------------------

class FlowCreate(BaseModel):
    from_location_id: int = Field(..., description="Origin location ID")
    to_location_id: int = Field(..., description="Destination location ID")
    visitor_count: int = Field(..., ge=1, description="Number of visitors in this flow")
    recorded_at: str | None = Field(None, description="Timestamp ISO-8601. Defaults to now.")


class FlowResponse(BaseModel):
    id: int
    from_location_id: int
    to_location_id: int
    visitor_count: int
    recorded_at: str
    created_at: str


class FlowMatrixCell(BaseModel):
    from_location_id: int
    from_location_name: str
    to_location_id: int
    to_location_name: str
    total_visitors: int
    flow_count: int


class FlowMatrixResponse(BaseModel):
    location_ids: list[int]
    location_names: dict[int, str]
    matrix: list[FlowMatrixCell]
    total_flows: int


class TopRouteEntry(BaseModel):
    from_location_id: int
    from_location_name: str
    to_location_id: int
    to_location_name: str
    total_visitors: int
    flow_count: int
    avg_daily_flow: float


class TopRoutesResponse(BaseModel):
    routes: list[TopRouteEntry]
    total_routes: int


class InboundFlowEntry(BaseModel):
    from_location_id: int
    from_location_name: str
    total_visitors: int
    flow_count: int


class InboundFlowResponse(BaseModel):
    location_id: int
    location_name: str
    inbound: list[InboundFlowEntry]
    total_inbound_visitors: int


class OutboundFlowEntry(BaseModel):
    to_location_id: int
    to_location_name: str
    total_visitors: int
    flow_count: int


class OutboundFlowResponse(BaseModel):
    location_id: int
    location_name: str
    outbound: list[OutboundFlowEntry]
    total_outbound_visitors: int


# -- Capacity Planning ---------------------------------------------------------

class CapacityUpdate(BaseModel):
    max_capacity: int = Field(..., ge=1, le=1_000_000, description="Maximum capacity for the location")


class CapacityResponse(BaseModel):
    location_id: int
    location_name: str
    max_capacity: int | None
    current_crowd_estimate: float | None
    utilization_pct: float | None


class CapacityOverviewEntry(BaseModel):
    location_id: int
    location_name: str
    category: str
    max_capacity: int
    current_crowd_estimate: float
    utilization_pct: float


class CapacityOverviewResponse(BaseModel):
    locations: list[CapacityOverviewEntry]
    total: int


class CapacityAlertEntry(BaseModel):
    location_id: int
    location_name: str
    category: str
    max_capacity: int
    current_crowd_estimate: float
    utilization_pct: float
    severity: str  # "warning" (80-99%) or "critical" (>=100%)


class CapacityAlertsResponse(BaseModel):
    alerts: list[CapacityAlertEntry]
    total: int


# -- Zone Templates ------------------------------------------------------------

class ZoneTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    default_category: str = Field("other", description="Default location category")
    default_tags: list[str] = Field(default_factory=list, max_length=20)
    analysis_config: dict = Field(default_factory=dict, description="Custom analysis configuration")


class ZoneTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    default_category: str | None = None
    default_tags: list[str] | None = Field(None, max_length=20)
    analysis_config: dict | None = None


class ZoneTemplateResponse(BaseModel):
    id: int
    name: str
    default_category: str
    default_tags: list[str]
    analysis_config: dict
    created_at: str
    updated_at: str


class ZoneTemplateDetailResponse(BaseModel):
    id: int
    name: str
    default_category: str
    default_tags: list[str]
    analysis_config: dict
    created_at: str
    updated_at: str
    applied_locations_count: int


class ZoneTemplateApplyResponse(BaseModel):
    template_id: int
    location_id: int
    applied_category: str
    applied_tags: list[str]
    message: str
