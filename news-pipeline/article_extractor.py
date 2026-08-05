#!/usr/bin/env python3
"""Isolated static-HTML extraction worker.

The parent process owns networking and validation. This worker receives one
bounded HTML document on stdin and returns only extracted text on stdout, so a
native parser failure cannot corrupt the long-lived daily pipeline process.
"""

from __future__ import annotations

import sys

import trafilatura


def main() -> int:
    page_html = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    text = trafilatura.extract(
        page_html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    ) or ""
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
