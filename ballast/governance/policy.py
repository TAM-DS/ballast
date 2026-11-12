from __future__ import annotations

from ballast.schema.models import Mitigation


class Denied(Exception):
    pass


def gate(action: Mitigation, approved: bool) -> None:
    if (action.disruptive or action.requires_approval) and approved is not True:
        raise Denied(f"approval required for {action.title}")

