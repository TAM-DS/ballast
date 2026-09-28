from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ballast.schema.models import Lane, Signal, Tenant, Ticket

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path("/tmp/ballast.db")
AUDIT_PATH = ROOT / "data" / "audit" / "events.jsonl"


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or DB_PATH)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._init()
        except OSError:
            self.path = Path("/tmp/ballast.db")
            self._init()

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
        return con

    def _init(self) -> None:
        with self._conn() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    name TEXT, industry TEXT, plan TEXT
                );
                CREATE TABLE IF NOT EXISTS lanes (
                    lane_id TEXT PRIMARY KEY,
                    tenant_id TEXT, origin TEXT, origin_region TEXT,
                    destination TEXT, commodity TEXT, annual_usd REAL,
                    delay_days REAL, concentration REAL, single_source INTEGER
                );
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    tenant_id TEXT, kind TEXT, topic TEXT, region TEXT,
                    severity TEXT, summary TEXT, horizon_days INTEGER
                );
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    tenant_id TEXT, title TEXT, body TEXT, customer TEXT,
                    lane_id TEXT, commodity TEXT, hours_open REAL
                );
                """
            )

    def upsert_tenant(self, t: Tenant) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO tenants VALUES (?,?,?,?)",
                (t.tenant_id, t.name, t.industry, t.plan),
            )

    def upsert_lane(self, l: Lane) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO lanes VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    l.lane_id, l.tenant_id, l.origin, l.origin_region,
                    l.destination, l.commodity, l.annual_usd, l.delay_days,
                    l.concentration, int(l.single_source),
                ),
            )

    def upsert_signal(self, s: Signal) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO signals VALUES (?,?,?,?,?,?,?,?)",
                (s.signal_id, s.tenant_id, s.kind, s.topic, s.region, s.severity.value, s.summary, s.horizon_days),
            )

    def upsert_ticket(self, t: Ticket) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO tickets VALUES (?,?,?,?,?,?,?,?)",
                (t.ticket_id, t.tenant_id, t.title, t.body, t.customer, t.lane_id, t.commodity, t.hours_open),
            )

    def tenants(self) -> list[Tenant]:
        with self._conn() as con:
            rows = con.execute("SELECT * FROM tenants ORDER BY name").fetchall()
        return [Tenant(**dict(r)) for r in rows]

    def lanes(self, tenant_id: str) -> list[Lane]:
        with self._conn() as con:
            rows = con.execute("SELECT * FROM lanes WHERE tenant_id=?", (tenant_id,)).fetchall()
        return [Lane(**{**dict(r), "single_source": bool(r["single_source"])}) for r in rows]

    def signals(self, tenant_id: str) -> list[Signal]:
        with self._conn() as con:
            rows = con.execute("SELECT * FROM signals WHERE tenant_id=?", (tenant_id,)).fetchall()
        return [Signal(**dict(r)) for r in rows]

    def tickets(self, tenant_id: str) -> list[Ticket]:
        with self._conn() as con:
            rows = con.execute("SELECT * FROM tickets WHERE tenant_id=?", (tenant_id,)).fetchall()
        return [Ticket(**dict(r)) for r in rows]


class Audit:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or AUDIT_PATH)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.path = Path("/tmp/ballast-audit.jsonl")

    def write(self, actor: str, action: str, detail: dict) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "actor": actor,
            "action": action,
            "detail": detail,
        }
        try:
            with self.path.open("a") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError:
            pass

    def tail(self, n: int = 16) -> list[str]:
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text().splitlines()[-n:]
        except OSError:
            return []
        out = []
        for line in lines:
            try:
                e = json.loads(line)
                out.append(f"{e['ts']} {e['actor']} {e['action']}")
            except Exception:
                continue
        return out
