from __future__ import annotations

import re

from ballast.schema.models import QueryFilters

COMMODITIES = {
    "semiconductor": "semiconductors",
    "semiconductors": "semiconductors",
    "chip": "semiconductors",
    "wafers": "semiconductors",
    "substrate": "substrates",
    "oil": "edible oils",
    "produce": "produce",
    "crude": "crude",
    "refined": "refined products",
}

REGIONS = {
    "taiwan": "Taiwan",
    "korea": "Korea",
    "china": "China",
    "mexico": "Mexico",
    "europe": "Europe",
    "gulf": "Gulf",
    "hormuz": "Gulf",
}


def parse_query(text: str) -> QueryFilters:
    raw = (text or "").strip()
    low = raw.lower()
    commodity = next((v for k, v in COMMODITIES.items() if k in low), None)
    region = next((v for k, v in REGIONS.items() if k in low), None)
    top = 5
    m = re.search(r"top\s+(\d+)", low)
    if m:
        top = max(1, min(10, int(m.group(1))))
    horizon = 30
    m = re.search(r"(\d+)\s+day", low)
    if m:
        horizon = int(m.group(1))
    return QueryFilters(commodity=commodity, region=region, horizon_days=horizon, top_n=top, raw=raw)
