import pytest
from pydantic import ValidationError
from ballast.runtime import Ballast
from ballast.schema.models import Scenario
from ballast.engine.risk import score_lane

@pytest.mark.parametrize('field,value', [('extra_delay_days', -1), ('extra_delay_days', float('nan')), ('tariff_shock', 101), ('tariff_shock', float('inf'))])
def test_invalid_scenario_rejected(field, value):
    with pytest.raises(ValidationError):
        Scenario(**{field: value})


def test_store_queries_keep_tenants_separate():
    rt = Ballast()
    for tenant in rt.store.tenants():
        for method in [rt.store.lanes, rt.store.signals, rt.store.tickets]:
            assert all(row.tenant_id == tenant.tenant_id for row in method(tenant.tenant_id))
            assert method("' OR 1=1 --") == []


def test_stress_is_bounded_and_does_not_change_baseline():
    rt = Ballast()
    for tenant in rt.store.tenants():
        signals = rt.store.signals(tenant.tenant_id)
        for lane in rt.store.lanes(tenant.tenant_id):
            initial = score_lane(lane, signals, Scenario())
            stressed = score_lane(lane, signals, Scenario(extra_delay_days=1000, tariff_shock=100))
            assert initial.score <= stressed.score <= 99
            assert score_lane(lane, signals, Scenario()) == initial
            assert stressed.usd_at_risk <= lane.annual_usd * .18 + 1
