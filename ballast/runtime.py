from __future__ import annotations

from ballast.engine.nl import parse_query
from ballast.engine.risk import score_lane
from ballast.engine.tickets import prioritize
from ballast.governance.policy import Denied, gate
from ballast.ingest.seed import seed
from ballast.memory.store import Audit, Store
from ballast.schema.models import Brief, Mitigation, Scenario


class Ballast:
    def __init__(self) -> None:
        self.store = Store()
        self.audit = Audit()
        seed(self.store)

    def tenant_labels(self) -> list[str]:
        return [f"{t.name} · {t.industry} · {t.tenant_id}" for t in self.store.tenants()]

    def tenant_id(self, label: str) -> str:
        return (label or "").rsplit("·", 1)[-1].strip()

    def run(self, tenant_label: str, query: str, scenario: Scenario) -> Brief:
        tid = self.tenant_id(tenant_label)
        q = parse_query(query)
        lanes = self.store.lanes(tid)
        signals = self.store.signals(tid)
        rows = [score_lane(l, signals, scenario) for l in lanes]
        if q.commodity:
            rows = [r for r in rows if q.commodity in r.commodity]
        if q.region:
            rows = [r for r in rows if q.region.lower() in r.origin_region.lower()]
        rows.sort(key=lambda r: r.score, reverse=True)
        rows = rows[: q.top_n]
        tickets = prioritize(self.store.tickets(tid), rows)
        narrative = self._narrative(tid, q, scenario, rows)
        self.audit.write("operator", "score", {"tenant": tid, "query": q.raw, "n": len(rows)})
        return Brief(tenant_id=tid, query=q, scenario=scenario, rows=rows, ticket_actions=tickets, narrative=narrative)

    def execute(self, brief: Brief, action_id: str, approved: bool) -> str:
        action: Mitigation | None = None
        for row in brief.rows:
            for m in row.mitigations:
                if m.action_id == action_id:
                    action = m
                    break
        if not action:
            return "Action not on this brief. Score the tenant first."
        try:
            gate(action, approved)
        except Denied as exc:
            self.audit.write("policy", "denied", {"action_id": action_id, "reason": str(exc)})
            return f"DENIED: {exc}"
        if action.disruptive:
            result = (
                f"[SIMULATED] {action.title} queued for {action.action_id}. "
                "Bookings and contracts unchanged until ops confirms."
            )
        else:
            result = f"[READ] {action.title} — synthetic intel attached to the lane."
        action.executed = True
        action.result = result
        self.audit.write("operator", "execute", {"action_id": action_id, "approved": approved})
        return result

    @staticmethod
    def _narrative(tid: str, q, scenario: Scenario, rows) -> str:
        if not rows:
            return "No lanes matched that filter. Clear the query or pick another tenant."
        top = rows[0]
        extras = []
        if scenario.typhoon_taiwan:
            extras.append("typhoon overlay is on")
        if scenario.port_closed:
            extras.append(f"port closed={scenario.port_closed}")
        if scenario.extra_delay_days:
            extras.append(f"+{scenario.extra_delay_days:.0f}d")
        extra = f" Scenario: {', '.join(extras)}." if extras else ""
        filt = q.commodity or q.region or "all commodities"
        return (
            f"{tid}: top risk is {top.title} at {top.score:.0f} ({top.severity.value}). "
            f"Filter={filt}, horizon={q.horizon_days}d, ${top.usd_at_risk:,.0f} at risk on the lead lane. "
            f"Disruptive mitigations stay behind an approval gate.{extra}"
        )
