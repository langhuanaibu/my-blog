import json
import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


ROOT = Path(__file__).resolve().parents[2]
DAILY_DIR = ROOT / "source" / "news" / "data" / "daily"


def _load_daily(path):
    raw = path.read_text(encoding="utf-8")
    match = re.search(r"window\.NEWS_DATA\[[^\]]+\] = (\{.*\});\s*$", raw, re.S)
    assert match, f"{path} has an invalid wrapper"
    return json.loads(match.group(1))


def test_legacy_quality_accepts_missing_same_day_duplicate_fields():
    payload = {
        "date": "2026-07-22",
        "quality": {
            "audited_events": 1,
            "split_events": 0,
            "removed_fields": 0,
            "degraded": False,
        },
        "items": [],
    }

    assert dn.validate_daily_payload(payload) == []


def test_all_daily_claims_and_themes_reference_published_rows():
    failures = []
    for path in sorted(DAILY_DIR.glob("*.js")):
        payload = _load_daily(path)
        rows = payload.get("items") or []
        item_ids = [row.get("id") for row in rows if isinstance(row, dict)]
        if len(item_ids) != len(set(item_ids)):
            failures.append(f"{path.name}: duplicate item ids")
        valid_ids = set(item_ids)
        for row in rows:
            names = {
                source.get("name") for source in (row.get("sources") or [])
                if isinstance(source, dict)
            }
            for claim in row.get("claims") or []:
                unknown = [
                    source for source in claim.get("sources") or []
                    if source not in names
                ]
                if unknown:
                    failures.append(
                        f"{path.name}:{row.get('id')} unknown claim sources {unknown}")
        for theme in payload.get("themes") or []:
            unknown = [
                item_id for item_id in theme.get("member_ids") or []
                if item_id not in valid_ids
            ]
            if unknown:
                failures.append(
                    f"{path.name}: unknown theme members {unknown}")

    assert failures == []
