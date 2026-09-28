import pytest

from ballast.engine.nl import parse_query
from ballast.governance.policy import Denied, gate
from ballast.runtime import Ballast
from ballast.schema.models import Mitigation, Scenario


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
