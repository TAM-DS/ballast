import pytest

from ballast.engine.nl import parse_query
from ballast.engine.risk import score_lane
from ballast.governance.policy import Denied, gate
from ballast.runtime import Ballast
from ballast.schema.models import Mitigation, Scenario
from ballast.ui.console import action_choices, scenario_comparison


def test_nl_taiwan_semiconductors():
    q = parse_query("Show me the top 5 risks to semiconductors from Taiwan in the next 30 days")
    assert q.commodity == "semiconductors"
    assert q.region == "Taiwan"
    assert q.top_n == 5
    assert q.horizon_days == 30


def test_unapproved_reroute_denied():
    with pytest.raises(Denied):
        gate(Mitigation(action_id="x", title="Reroute", disruptive=True, requires_approval=True), approved=False)


def test_score_chip_tenant():
    rt = Ballast()
    label = next(x for x in rt.tenant_labels() if "ten-chip" in x)
    brief = rt.run(label, "top 5 risks to semiconductors from Taiwan in the next 30 days", Scenario())
    assert brief.rows
    assert all("Taiwan" in r.origin_region or r.commodity == "semiconductors" for r in brief.rows)
    hard = next(m for r in brief.rows for m in r.mitigations if m.requires_approval)
    assert "DENIED" in rt.execute(brief, hard.action_id, approved=False)
    assert "[SIMULATED]" in rt.execute(brief, hard.action_id, approved=True)


def test_scenario_comparison_uses_actual_engine_scores():
    rt = Ballast()
    label = next(x for x in rt.tenant_labels() if "ten-chip" in x)
    scenario = Scenario(extra_delay_days=3, typhoon_taiwan=True)
    brief = rt.run(label, "top 5 risks to semiconductors from Taiwan in the next 30 days", scenario)
    signals = rt.store.signals(brief.tenant_id)
    baselines = {
        lane.lane_id: score_lane(lane, signals, Scenario())
        for lane in rt.store.lanes(brief.tenant_id)
    }
    comparison = scenario_comparison(brief, baselines)
    assert "Baseline" in comparison and "Scenario" in comparison
    assert "Taiwan typhoon overlay" in comparison
    assert "+3 days delay" in comparison
    for row in brief.rows:
        initial = baselines[row.lane_id]
        change = row.score - initial.score
        delta = f"{change:+.1f}" if change else "0.0"
        assert f"| {initial.score:.1f} | {row.score:.1f} | {delta} |" in comparison
        assert row.score >= initial.score


def test_action_choices_remain_stable_when_execution_status_changes():
    rt = Ballast()
    label = next(x for x in rt.tenant_labels() if "ten-chip" in x)
    brief = rt.run(label, "top 5 risks to semiconductors from Taiwan in the next 30 days", Scenario())
    before = action_choices(brief)
    assert before
    brief.rows[0].mitigations[0].executed = True
    assert action_choices(brief) == before
