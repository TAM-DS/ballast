from __future__ import annotations

from ballast.schema.models import RiskRow, Ticket


def prioritize(tickets: list[Ticket], rows: list[RiskRow]) -> list[dict]:
    by_lane = {r.lane_id: r for r in rows}
    out = []
    for t in tickets:
        row = by_lane.get(t.lane_id or "")
        score = 20 + min(t.hours_open, 72) * 0.6
        if row:
            score += row.score * 0.5
        usd = row.usd_at_risk if row else 0
        if score >= 70:
            action = "Escalate to control tower — lane already high risk"
        elif "dual" in t.body.lower() or "source" in t.title.lower():
            action = "Draft dual-source note (approval required to send)"
        else:
            action = "Reply with current delay + next milestone"
        out.append(
            {
                "ticket_id": t.ticket_id,
                "title": t.title,
                "customer": t.customer,
                "hours_open": t.hours_open,
                "priority": round(score, 1),
                "usd_at_risk": usd,
                "action": action,
            }
        )
    out.sort(key=lambda x: x["priority"], reverse=True)
    return out
