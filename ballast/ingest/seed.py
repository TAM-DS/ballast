from __future__ import annotations

from ballast.memory.store import Store
from ballast.schema.models import Lane, Signal, Severity, Tenant, Ticket


def seed(store: Store) -> None:
    tenants = [
        Tenant(tenant_id="ten-chip", name="Northwind Semiconductors", industry="semiconductors", plan="firm"),
        Tenant(tenant_id="ten-food", name="Gulf Harvest Imports", industry="food", plan="operator"),
        Tenant(tenant_id="ten-energy", name="Cinder Point Trading", industry="energy", plan="firm"),
    ]
    for t in tenants:
        store.upsert_tenant(t)

    lanes = [
        Lane(lane_id="ln-tpe-aus", tenant_id="ten-chip", origin="Taipei", origin_region="Taiwan",
             destination="Austin", commodity="semiconductors", annual_usd=420_000_000,
             delay_days=6, concentration=0.72, single_source=True),
        Lane(lane_id="ln-tpe-phx", tenant_id="ten-chip", origin="Kaohsiung", origin_region="Taiwan",
             destination="Phoenix", commodity="semiconductors", annual_usd=190_000_000,
             delay_days=3, concentration=0.55, single_source=True),
        Lane(lane_id="ln-pus-sjc", tenant_id="ten-chip", origin="Busan", origin_region="Korea",
             destination="San Jose", commodity="substrates", annual_usd=48_000_000,
             delay_days=2, concentration=0.31, single_source=False),
        Lane(lane_id="ln-sha-hou", tenant_id="ten-food", origin="Shanghai", origin_region="China",
             destination="Houston", commodity="edible oils", annual_usd=22_000_000,
             delay_days=11, concentration=0.48, single_source=False),
        Lane(lane_id="ln-ver-dal", tenant_id="ten-food", origin="Veracruz", origin_region="Mexico",
             destination="Dallas", commodity="produce", annual_usd=9_400_000,
             delay_days=1, concentration=0.22, single_source=False),
        Lane(lane_id="ln-rot-hou", tenant_id="ten-energy", origin="Rotterdam", origin_region="Europe",
             destination="Houston", commodity="refined products", annual_usd=310_000_000,
             delay_days=4, concentration=0.41, single_source=False),
        Lane(lane_id="ln-hormuz", tenant_id="ten-energy", origin="Ras Tanura", origin_region="Gulf",
             destination="Rotterdam", commodity="crude", annual_usd=890_000_000,
             delay_days=5, concentration=0.63, single_source=False),
    ]
    for l in lanes:
        store.upsert_lane(l)

    signals = [
        Signal(signal_id="sig-typhoon", tenant_id="ten-chip", kind="weather", topic="typhoon",
               region="Taiwan", severity=Severity.high,
               summary="Synthetic typhoon track threatens Kaohsiung window in 8-14 days."),
        Signal(signal_id="sig-strait", tenant_id="ten-chip", kind="geo", topic="strait-tension",
               region="Taiwan", severity=Severity.high,
               summary="Elevated insurance quotes on Taiwan Strait box routes."),
        Signal(signal_id="sig-lead", tenant_id="ten-chip", kind="delay", topic="lead-time",
               region="Taiwan", severity=Severity.medium,
               summary="Foundry outbound dwell +2.1 days vs 30-day baseline."),
        Signal(signal_id="sig-port", tenant_id="ten-food", kind="delay", topic="congestion",
               region="China", severity=Severity.medium,
               summary="Shanghai export yard dwell elevated; reefers waiting."),
        Signal(signal_id="sig-hormuz", tenant_id="ten-energy", kind="geo", topic="chokepoint",
               region="Gulf", severity=Severity.critical,
               summary="Synthetic chokepoint alert on Hormuz-adjacent liftings."),
    ]
    for s in signals:
        store.upsert_signal(s)

    tickets = [
        Ticket(ticket_id="tix-401", tenant_id="ten-chip", title="Austin line-down risk",
               body="Fab asking where the TSMC wafers are. Second week of slip.",
               customer="Austin Fab Ops", lane_id="ln-tpe-aus", commodity="semiconductors", hours_open=36),
        Ticket(ticket_id="tix-402", tenant_id="ten-chip", title="Need dual source on ABF",
               body="Procurement wants a Korea substrate option in writing.",
               customer="Strategic Sourcing", lane_id="ln-pus-sjc", commodity="substrates", hours_open=12),
        Ticket(ticket_id="tix-220", tenant_id="ten-food", title="Oil shipment late for private label",
               body="Retailer will charge back if Houston misses Friday.",
               customer="Gulf Harvest CS", lane_id="ln-sha-hou", commodity="edible oils", hours_open=20),
        Ticket(ticket_id="tix-880", tenant_id="ten-energy", title="Desk wants Hormuz overlay",
               body="Trading asked for a 30-day disruption overlay on crude.",
               customer="Cinder Point Desk", lane_id="ln-hormuz", commodity="crude", hours_open=6),
    ]
    for t in tickets:
        store.upsert_ticket(t)
