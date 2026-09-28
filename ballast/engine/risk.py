from __future__ import annotations

from ballast.schema.models import Lane, Mitigation, RiskRow, Scenario, Severity, Signal

WEIGHTS = {
    "delay": 6.0,
    "concentration": 28.0,
    "single_source": 18.0,
    "signal": 22.0,
    "scenario": 24.0,
}


def _sev(score: float) -> Severity:
    if score >= 80:
        return Severity.critical
    if score >= 62:
        return Severity.high
    if score >= 40:
        return Severity.medium
    return Severity.low


def score_lane(lane: Lane, signals: list[Signal], scenario: Scenario) -> RiskRow:
    drivers: list[str] = []
    score = 12.0 + min(lane.delay_days, 21) * WEIGHTS["delay"] / 3
    if lane.delay_days >= 4:
        drivers.append(f"baseline delay {lane.delay_days:.1f}d")
    score += lane.concentration * WEIGHTS["concentration"]
    if lane.concentration >= 0.5:
        drivers.append(f"concentration {lane.concentration:.0%}")
    if lane.single_source:
        score += WEIGHTS["single_source"]
        drivers.append("single source")

    related = [s for s in signals if _hits(s, lane)]
    if related:
        bump = max({"low": 6, "medium": 12, "high": 18, "critical": 24}[s.severity.value] for s in related)
        score += bump
        drivers.append(related[0].summary)

    score += _scenario_bump(lane, scenario, drivers)
    score = max(0.0, min(99.0, score))
    usd = lane.annual_usd * (score / 100.0) * 0.18
    return RiskRow(
        lane_id=lane.lane_id,
        title=f"{lane.origin} → {lane.destination} ({lane.commodity})",
        commodity=lane.commodity,
        origin_region=lane.origin_region,
        score=round(score, 1),
        severity=_sev(score),
        drivers=drivers[:4],
        usd_at_risk=round(usd, 0),
        mitigations=_mitigations(lane, score),
    )


def _hits(signal: Signal, lane: Lane) -> bool:
    blob = f"{signal.region} {signal.topic} {signal.summary}".lower()
    return lane.origin_region.lower() in blob or lane.commodity.lower() in blob or lane.origin.lower() in blob


def _scenario_bump(lane: Lane, sc: Scenario, drivers: list[str]) -> float:
    bump = sc.extra_delay_days * 2.2
    if sc.extra_delay_days:
        drivers.append(f"+{sc.extra_delay_days:.0f}d scenario delay")
    if sc.tariff_shock:
        bump += sc.tariff_shock * 0.35
        drivers.append(f"tariff shock {sc.tariff_shock:.0f}%")
    port = (sc.port_closed or "").lower()
    if port and port in f"{lane.origin} {lane.destination} {lane.origin_region}".lower():
        bump += 22
        drivers.append(f"port closed: {sc.port_closed}")
    if sc.typhoon_taiwan and "taiwan" in lane.origin_region.lower():
        bump += 20
        drivers.append("typhoon overlay on Taiwan lanes")
    return bump


def _mitigations(lane: Lane, score: float) -> list[Mitigation]:
    acts = [
        Mitigation(
            action_id=f"act-read-{lane.lane_id}",
            title="Pull dwell and insurance quotes",
            description="Read-only enrichment against the synthetic intel store.",
        )
    ]
    if lane.single_source or score >= 55:
        acts.append(
            Mitigation(
                action_id=f"act-dual-{lane.lane_id}",
                title="Open dual-source RFQ",
                description=f"Draft RFQ for an alternate origin on {lane.commodity}.",
                disruptive=True,
                requires_approval=True,
            )
        )
    if score >= 70:
        acts.append(
            Mitigation(
                action_id=f"act-reroute-{lane.lane_id}",
                title="Reroute active POs",
                description=f"Propose reroute off {lane.origin} → {lane.destination}. Does not change bookings until ops confirms.",
                disruptive=True,
                requires_approval=True,
            )
        )
    return acts
