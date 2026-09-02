#!/usr/bin/env python3
"""匯出待 Cursor Agent 分析的標案清單。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analyze import format_days_left
from config import DATA_DIR
from database import init_db, list_pending_analysis
from fetch_detail import is_expired_on
from pcc_utils import today_taipei

PENDING_PATH = DATA_DIR / "pending_analysis.json"


def tender_to_dict(item, today) -> dict:
    return {
        "tender_id": item.tender_id,
        "unit_id": item.unit_id,
        "job_number": item.job_number,
        "title": item.title,
        "unit_name": item.unit_name,
        "budget": item.budget,
        "start_date": item.start_date,
        "deadline": item.deadline,
        "days_left": format_days_left(item.deadline_date, today),
        "location": item.location,
        "method": item.method,
        "is_electronic_bid": item.is_electronic_bid,
        "is_electronic_pickup": item.is_electronic_pickup,
        "matched_keywords": item.matched_keywords,
        "url": item.url,
        "first_seen": item.first_seen,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="匯出待分析標案")
    parser.add_argument(
        "--output",
        default=str(PENDING_PATH),
        help="輸出 JSON 路徑（預設 data/pending_analysis.json）",
    )
    args = parser.parse_args()

    init_db()
    today = today_taipei()
    pending = [
        item
        for item in list_pending_analysis()
        if not is_expired_on(item.deadline_date, today)
    ]

    payload = {
        "date": today.isoformat(),
        "count": len(pending),
        "tenders": [tender_to_dict(item, today) for item in pending],
        "analysis_template": {
            "sections": [
                "【案件簡述】",
                "【與雜波契合度】",
                "【技術與履約重點】",
                "【風險與注意事項】",
                "【行動建議】",
            ],
            "company": "雜波 — 中小型公共藝術執行、互動裝置開發",
            "budget_range": "70～300 萬",
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Pending analysis: {len(pending)}")
    print(f"Written to: {output_path}")
    for item in pending:
        print(f"  - {item.tender_id}: {item.title[:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
