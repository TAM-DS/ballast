import json
import pytest
from ballast.runtime import Ballast
from ballast.schema.models import Mitigation, Scenario
from ballast.governance.policy import Denied, gate

@pytest.mark.parametrize('approved', [False, None, 'false', 'true', 1])
def test_approval_requires_explicit_boolean(approved):
    with pytest.raises(Denied):
        gate(Mitigation(action_id='x', title='Review', requires_approval=True), approved)


def test_readonly_action_needs_no_approval():
    gate(Mitigation(action_id='x', title='Read'), False)


def proposed_action():
    rt = Ballast()
    label = next(x for x in rt.tenant_labels() if 'ten-chip' in x)
    brief = rt.run(label, 'top 5 risks', Scenario())
    action = next(m for r in brief.rows for m in r.mitigations if m.requires_approval)
    return rt, brief, action


def test_denial_leaves_action_unchanged_and_records_reason():
    rt, brief, action = proposed_action()
    assert rt.execute(brief, action.action_id, False).startswith('DENIED')
    assert not action.executed and action.result == ''
    event = json.loads(rt.audit.path.read_text().splitlines()[-1])
    assert event['action'] == 'denied'
    assert event['detail']['action_id'] == action.action_id


def test_audit_failure_cannot_mark_execution_successful(monkeypatch):
    rt, brief, action = proposed_action()
    def fail(*args):
        raise OSError('disk unavailable')
    monkeypatch.setattr(rt.audit, 'write', fail)
    with pytest.raises(OSError):
        rt.execute(brief, action.action_id, True)
    assert not action.executed and action.result == ''


def test_unknown_action_does_not_execute_anything():
    rt, brief, _ = proposed_action()
    assert rt.execute(brief, 'not-on-brief', True).startswith('Action not on')
    assert all(not m.executed for r in brief.rows for m in r.mitigations)
