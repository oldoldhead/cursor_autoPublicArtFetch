#!/usr/bin/env python3
"""寫入 Cursor Agent 產生的標案分析。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from database import get_tender, init_db, make_tender_id, set_analysis


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="寫入標案 AI 分析（供 Cursor Agent 使用）")
    parser.add_argument("--tender-id", help="標案 ID，格式 unit_id:job_number")
    parser.add_argument("--unit-id", help="機關代碼（與 --job-number 合用）")
    parser.add_argument("--job-number", help="標案案號（與 --unit-id 合用）")
    parser.add_argument("--analysis", help="分析文字")
    parser.add_argument("--file", help="分析文字檔案路徑")
    args = parser.parse_args()

    tender_id = args.tender_id
    if not tender_id and args.unit_id and args.job_number:
        tender_id = make_tender_id(args.unit_id, args.job_number)
    if not tender_id:
        print("Error: 請提供 --tender-id 或 --unit-id + --job-number", file=sys.stderr)
        return 1

    if args.file:
        analysis = Path(args.file).read_text(encoding="utf-8")
    elif args.analysis:
        analysis = args.analysis
    else:
        print("Error: 請提供 --analysis 或 --file", file=sys.stderr)
        return 1

    init_db()
    if not get_tender(tender_id):
        print(f"Error: 找不到標案 {tender_id}", file=sys.stderr)
        return 1

    if set_analysis(tender_id, analysis):
        print(f"Analysis saved: {tender_id}")
        return 0

    print(f"Error: 無法寫入 {tender_id}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
