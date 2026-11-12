import pytest
from ballast.memory import store

@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'ballast.db')
    monkeypatch.setattr(store, 'AUDIT_PATH', tmp_path / 'events.jsonl')
