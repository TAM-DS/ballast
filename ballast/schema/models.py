from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Tenant(BaseModel):
    tenant_id: str
    name: str
    industry: str
    plan: str = "operator"


class Lane(BaseModel):
    lane_id: str
    tenant_id: str
    origin: str
    origin_region: str
    destination: str
    commodity: str
    annual_usd: float
    delay_days: float = 0.0
    concentration: float = 0.4
    single_source: bool = False


class Signal(BaseModel):
    signal_id: str
    tenant_id: str
    kind: str
    topic: str
    region: str
    severity: Severity
    summary: str
    horizon_days: int = 30


class Ticket(BaseModel):
    ticket_id: str
    tenant_id: str
    title: str
    body: str
    customer: str
    lane_id: str | None = None
    commodity: str | None = None
    hours_open: float = 4.0


class Mitigation(BaseModel):
    action_id: str
    title: str
    description: str = ""
    disruptive: bool = False
    requires_approval: bool = False
    executed: bool = False
    result: str = ""


class RiskRow(BaseModel):
    lane_id: str
    title: str
    commodity: str
    origin_region: str
    score: float
    severity: Severity
    drivers: list[str] = Field(default_factory=list)
    usd_at_risk: float = 0.0
    mitigations: list[Mitigation] = Field(default_factory=list)


class Scenario(BaseModel):
    port_closed: str = ""
    extra_delay_days: float = 0.0
    tariff_shock: float = 0.0
    typhoon_taiwan: bool = False


class QueryFilters(BaseModel):
    commodity: str | None = None
    region: str | None = None
    horizon_days: int = 30
    top_n: int = 5
    raw: str = ""


class Brief(BaseModel):
    tenant_id: str
    query: QueryFilters
    scenario: Scenario
    rows: list[RiskRow]
    ticket_actions: list[dict[str, Any]] = Field(default_factory=list)
    narrative: str = ""
