from scripts.export_demo import export


def test_export_replays_and_keeps_gate_outcomes_honest():
    data = export()
    assert export() == data
    assert data['mode'] == 'synthetic-precomputed'
    assert len(data['scenarios']) == 4
    for scenario in data['scenarios']:
        assert scenario['brief']['rows']
        for action in scenario['actions']:
            if action['requires_approval']:
                assert action['without_approval'].startswith('DENIED:')
                assert action['with_approval'].startswith('[SIMULATED]')
            else:
                assert action['without_approval'].startswith('[READ]')
    assert data['source_files']['ballast/engine/risk.py']
