"""Run a parallel, time-bounded careers scan straight against the database.

Intended for GitHub Actions (no gateway timeout, headless Chromium installable):

    DATABASE_URL=... python scripts/run_scan.py --limit 400 --max-seconds 2400 --workers 8

Set JS_RENDER_ENABLED=true (and have Playwright's Chromium installed) to also read
JavaScript-rendered careers pages. Exits 0 on a normal run, even if some sources fail.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=400, help="max companies to scan this run")
    ap.add_argument("--max-seconds", type=float, default=2400.0,
                    help="stop starting new scans after this many seconds")
    ap.add_argument("--workers", type=int, default=8, help="concurrent scans")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from app.db.session import SessionLocal
    from app.services.scan_runner import scan_due_parallel

    summary = scan_due_parallel(SessionLocal, limit=args.limit,
                                max_seconds=args.max_seconds, workers=args.workers)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
