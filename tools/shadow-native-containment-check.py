#!/usr/bin/env python3
"""Diagnostic-only native parser containment check for GitHub Actions."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def load_daily_news():
    path = ROOT / "news-pipeline" / "daily_news.py"
    spec = importlib.util.spec_from_file_location("daily_news", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    daily_news = load_daily_news()
    fixture = (ROOT / "news-pipeline" / "tests" / "fixtures" /
               "article-extractor-minimal.html").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as directory:
        temp_dir = Path(directory)
        abort_worker = temp_dir / "abort_worker.py"
        abort_worker.write_text(
            "import os\nimport sys\nsys.stdin.buffer.read()\n"
            "if sys.platform != 'win32':\n"
            " import resource\n resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
            "os._exit(134) if sys.platform == 'win32' else os.abort()\n",
            encoding="utf-8",
        )
        for _ in range(20):
            try:
                daily_news._extract_static_article(
                    fixture,
                    timeout=1.0,
                    command=[sys.executable, str(abort_worker)],
                )
            except daily_news.ArticleEvidenceError as exc:
                if "subprocess exited" not in str(exc):
                    raise
            else:
                raise AssertionError("native abort unexpectedly succeeded")

        blocking_worker = temp_dir / "blocking_worker.py"
        blocking_worker.write_text(
            "import sys\nimport time\nsys.stdin.buffer.read()\ntime.sleep(30)\n",
            encoding="utf-8",
        )
        started = time.perf_counter()
        try:
            daily_news._extract_static_article(
                fixture,
                timeout=0.05,
                command=[sys.executable, str(blocking_worker)],
            )
        except daily_news.ArticleEvidenceError as exc:
            if "timed out" not in str(exc):
                raise
        else:
            raise AssertionError("blocking parser unexpectedly succeeded")
        if time.perf_counter() - started >= 1.0:
            raise AssertionError("blocking parser was not terminated promptly")

    extracted = daily_news._extract_static_article(fixture, timeout=5.0)
    if "Synthetic evidence report" not in extracted:
        raise AssertionError("healthy extraction did not complete after crash pressure")
    print("contained 20 native exits, reaped timeout, completed healthy extraction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
