"""Export synthetic results for the static recruiter walkthrough; no live services."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ballast.runtime import Ballast
from ballast.memory.store import Store, Audit
from ballast.schema.models import Scenario


def export():
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((ROOT/'ballast').rglob('*.py'))}
    result = {'mode': 'synthetic-precomputed', 'source_files': sources, 'scenarios': []}
    with tempfile.TemporaryDirectory() as temp:
        rt = Ballast(Store(Path(temp)/'demo.db'), Audit(Path(temp)/'audit.jsonl'))
        for tid, title, query, stress in [
            ('ten-energy', 'Energy delivery', 'top 5 risks', Scenario(port_closed='Ras Tanura', extra_delay_days=3)),
            ('ten-chip', 'Semiconductor supply', 'top 5 risks to semiconductors from Taiwan', Scenario(typhoon_taiwan=True, extra_delay_days=3)),
        ]:
            label = next(x for x in rt.tenant_labels() if tid in x)
            for name, scenario in [('Baseline', Scenario()), ('Disruption', stress)]:
                brief = rt.run(label, query, scenario)
                actions = []
                for row in brief.rows:
                    for action in row.mitigations:
                        actions.append({
                            'lane': row.title, 'id': action.action_id, 'title': action.title,
                            'requires_approval': action.disruptive or action.requires_approval,
                            'without_approval': rt.execute(brief.model_copy(deep=True), action.action_id, False),
                            'with_approval': rt.execute(brief.model_copy(deep=True), action.action_id, True),
                        })
                result['scenarios'].append({'id': f'{tid}-{name.lower()}', 'title': title,
                    'variant': name, 'brief': brief.model_dump(mode='json'), 'actions': actions})
    return result


if __name__ == '__main__':
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'demo-fixtures.json'
    destination.write_text(json.dumps(export(), indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(destination)
