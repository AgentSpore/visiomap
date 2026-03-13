"""v1.7.0 services — Visitor Flow Analysis, Capacity Planning, Zone Templates."""
from __future__ import annotations

import json
from typing import Any

from visiomap.repositories.location_repo import LocationRepo
from visiomap.repositories.v170_repo import CapacityRepo, FlowRepo, ZoneTemplateRepo


# ==============================================================================
# Flow Service
# ==============================================================================

class FlowService:
    def __init__(self, flow_repo: FlowRepo, location_repo: LocationRepo) -> None:
        self.flow_repo = flow_repo
        self.location_repo = location_repo

    async def create_flow(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Record a visitor flow. Returns None if either location doesn't exist."""
        if not await self.location_repo.exists(data["from_location_id"]):
            return None
        if not await self.location_repo.exists(data["to_location_id"]):
            return None
        return await self.flow_repo.create(data)

    async def list_flows(
        self,
        from_id: int | None = None,
        to_id: int | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.flow_repo.list_all(from_id, to_id, since, until, limit, offset)

    async def get_matrix(self) -> dict[str, Any]:
        """Build an origin-destination matrix."""
        cells = await self.flow_repo.get_matrix()
        # Collect all location ids and names
        loc_ids: set[int] = set()
        loc_names: dict[int, str] = {}
        for cell in cells:
            loc_ids.add(cell["from_location_id"])
            loc_ids.add(cell["to_location_id"])
            loc_names[cell["from_location_id"]] = cell["from_location_name"]
            loc_names[cell["to_location_id"]] = cell["to_location_name"]
        return {
            "location_ids": sorted(loc_ids),
            "location_names": loc_names,
            "matrix": cells,
            "total_flows": sum(c["flow_count"] for c in cells),
        }

    async def get_top_routes(self, top_n: int = 10) -> dict[str, Any]:
        routes = await self.flow_repo.get_top_routes(top_n)
        return {
            "routes": routes,
            "total_routes": len(routes),
        }

    async def get_inbound(self, location_id: int) -> dict[str, Any] | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        inbound = await self.flow_repo.get_inbound(location_id)
        total = sum(e["total_visitors"] for e in inbound)
        return {
            "location_id": location["id"],
            "location_name": location["name"],
            "inbound": inbound,
            "total_inbound_visitors": total,
        }

    async def get_outbound(self, location_id: int) -> dict[str, Any] | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        outbound = await self.flow_repo.get_outbound(location_id)
        total = sum(e["total_visitors"] for e in outbound)
        return {
            "location_id": location["id"],
            "location_name": location["name"],
            "outbound": outbound,
            "total_outbound_visitors": total,
        }


# ==============================================================================
# Capacity Service
# ==============================================================================

class CapacityService:
    def __init__(self, capacity_repo: CapacityRepo, location_repo: LocationRepo) -> None:
        self.capacity_repo = capacity_repo
        self.location_repo = location_repo

    async def set_capacity(self, location_id: int, max_capacity: int) -> dict[str, Any] | None:
        if not await self.capacity_repo.set_capacity(location_id, max_capacity):
            return None
        return await self.capacity_repo.get_capacity(location_id)

    async def get_capacity(self, location_id: int) -> dict[str, Any] | None:
        return await self.capacity_repo.get_capacity(location_id)

    async def get_overview(self) -> dict[str, Any]:
        locations = await self.capacity_repo.get_all_with_capacity()
        return {
            "locations": locations,
            "total": len(locations),
        }

    async def get_alerts(self) -> dict[str, Any]:
        """Return locations where utilization >= 80%."""
        all_locs = await self.capacity_repo.get_all_with_capacity()
        alerts = []
        for loc in all_locs:
            util = loc["utilization_pct"]
            if util >= 80.0:
                severity = "critical" if util >= 100.0 else "warning"
                alerts.append({**loc, "severity": severity})
        # Sort by utilization descending (most critical first)
        alerts.sort(key=lambda a: a["utilization_pct"], reverse=True)
        return {
            "alerts": alerts,
            "total": len(alerts),
        }


# ==============================================================================
# Zone Template Service
# ==============================================================================

class ZoneTemplateService:
    def __init__(
        self,
        template_repo: ZoneTemplateRepo,
        location_repo: LocationRepo,
    ) -> None:
        self.template_repo = template_repo
        self.location_repo = location_repo

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self.template_repo.create(data)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        return await self.template_repo.list_all(limit, offset)

    async def get_detail(self, template_id: int) -> dict[str, Any] | None:
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return None
        count = await self.template_repo.count_applied_locations(template_id)
        return {**template, "applied_locations_count": count}

    async def update(self, template_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        return await self.template_repo.update(template_id, data)

    async def delete(self, template_id: int) -> str | None:
        """Delete template. Returns error message string or None on success.
        Returns 'not_found' if template doesn't exist.
        Returns 'in_use' if locations are still using it.
        """
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return "not_found"
        if await self.template_repo.is_applied_anywhere(template_id):
            return "in_use"
        await self.template_repo.delete(template_id)
        return None

    async def apply_to_location(
        self, template_id: int, location_id: int,
    ) -> dict[str, Any] | None:
        """Apply template settings to a location. Returns apply result or None."""
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return None
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None

        # Apply template fields to location
        update_data: dict[str, Any] = {}
        if template["default_category"]:
            update_data["category"] = template["default_category"]
        if template["default_tags"]:
            # Merge tags: existing + template, deduplicated
            existing_tags = set(location.get("tags", []))
            new_tags = list(existing_tags | set(template["default_tags"]))
            update_data["tags"] = new_tags

        if update_data:
            await self.location_repo.update(location_id, update_data)

        # Record the association
        await self.template_repo.apply_to_location(template_id, location_id)

        # Reload location for response
        updated_loc = await self.location_repo.get_by_id(location_id)
        return {
            "template_id": template_id,
            "location_id": location_id,
            "applied_category": updated_loc.get("category", template["default_category"]),
            "applied_tags": updated_loc.get("tags", []),
            "message": f"Template '{template['name']}' applied to location '{updated_loc['name']}'",
        }

    async def get_locations(self, template_id: int) -> list[dict[str, Any]] | None:
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return None
        return await self.template_repo.get_applied_locations(template_id)
