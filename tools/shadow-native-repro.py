#!/usr/bin/env python3
"""Replay public article evidence extraction without LLMs or repository writes."""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def load_daily_news():
    path = ROOT / "news-pipeline" / "daily_news.py"
    spec = importlib.util.spec_from_file_location("daily_news", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_urls(date: str, limit: int) -> list[str]:
    path = ROOT / "source" / "news" / "data" / "daily" / f"{date}.js"
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw[raw.index("= {") + 2 :].rsplit(";", 1)[0])
    urls: list[str] = []
    for item in payload.get("items", []):
        for source in item.get("sources", []):
            url = str(source.get("url") or "")
            if url and url not in urls:
                urls.append(url)
    return urls[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-08-05")
    parser.add_argument("--limit", type=int, default=72)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    daily_news = load_daily_news()
    urls = load_urls(args.date, args.limit)
    if not urls:
        raise SystemExit("no source URLs found")
    print(json.dumps({"date": args.date, "urls": len(urls), "rounds": args.rounds,
                      "workers": args.workers, "timeout": args.timeout}), flush=True)

    def fetch(url: str):
        return daily_news.fetch_article_evidence(
            {"url": url, "title": "repro", "desc": "RSS fallback" * 20},
            attempt_timeout=args.timeout,
            max_attempts=1,
        )

    started = time.perf_counter()
    totals = {"fulltext": 0, "snippet": 0}
    for round_index in range(args.rounds):
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            rows = list(pool.map(fetch, urls))
        fulltext = sum(row["evidence_basis"] == "fulltext" for row in rows)
        totals["fulltext"] += fulltext
        totals["snippet"] += len(rows) - fulltext
        print(json.dumps({"round": round_index + 1, "fulltext": fulltext,
                          "snippet": len(rows) - fulltext}), flush=True)
    print(json.dumps({**totals, "seconds": round(time.perf_counter() - started, 3)}),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
