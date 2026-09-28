from __future__ import annotations

from ballast.schema.models import Mitigation


class Denied(Exception):
    pass


def gate(action: Mitigation, approved: bool) -> None:
    if action.disruptive and not approved:
        raise Denied(f"approval required for {action.title}")
