#!/usr/bin/env python3
"""雜波標案每日監控 — 主程式。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date

from database import (
    TenderRow,
    count_pending_analysis,
    get_tender,
    init_db,
    list_active_tenders,
    make_tender_id,
    mark_expired_before,
    now_iso,
    reset_all_tenders,
    upsert_tender,
)
from email_template import ReportSummary, build_html, build_subject
from config import MIN_DAYS_LEFT
from fetch_detail import is_expired_on
from pcc_utils import today_taipei
from search import find_high_relevance_tenders
from send_email import send_html_email


def sync_search_results(today: date, use_openai: bool = False) -> tuple[int, int]:
    from analyze import analyze_tender

    found = find_high_relevance_tenders(today)
    new_count = 0
    updated_count = 0

    for item in found:
        tender_id = make_tender_id(item["unit_id"], item["job_number"])
        existing = get_tender(tender_id)
        is_new = existing is None

        ai_analysis = None
        analyzed_at = None
        first_seen = today.isoformat()

        if existing:
            first_seen = existing.first_seen
            ai_analysis = existing.ai_analysis
            analyzed_at = existing.analyzed_at

        if is_new and use_openai:
            ai_analysis = analyze_tender(
                title=item["title"],
                unit_name=item["unit_name"],
                budget=item["budget"],
                method=item["method"],
                location=item["location"],
                deadline=item["deadline"],
                deadline_date=item["deadline_date"],
                today=today,
            )
            analyzed_at = now_iso()
        if is_new:
            new_count += 1
        else:
            updated_count += 1

        row = TenderRow(
            tender_id=tender_id,
            unit_id=item["unit_id"],
            job_number=item["job_number"],
            title=item["title"],
            unit_name=item["unit_name"],
            budget=item["budget"],
            start_date=item["start_date"],
            deadline=item["deadline"],
            deadline_date=item["deadline_date"],
            is_electronic_bid=item["is_electronic_bid"],
            is_electronic_pickup=item["is_electronic_pickup"],
            url=item["url"],
            method=item["method"],
            location=item["location"],
            relevance_score=item["relevance_score"],
            matched_keywords=item["matched_keywords"],
            ai_analysis=ai_analysis,
            analyzed_at=analyzed_at,
            first_seen=first_seen,
            status="active",
            last_in_report=today.isoformat(),
        )
        upsert_tender(row)

    return new_count, updated_count


def build_report_summary(today: date, expired_count: int) -> ReportSummary:
    active = list_active_tenders()
    active = [
        item
        for item in active
        if item.deadline_date is not None
        and not is_expired_on(item.deadline_date, today)
        and (item.deadline_date - today).days >= MIN_DAYS_LEFT
    ]

    new_items = [item for item in active if item.first_seen == today.isoformat()]
    tracking_items = [item for item in active if item.first_seen != today.isoformat()]

    new_items.sort(key=lambda x: (x.deadline_date or date.max, -x.budget))
    tracking_items.sort(key=lambda x: (x.deadline_date or date.max, -x.budget))

    return ReportSummary(
        report_date=today,
        new_items=new_items,
        tracking_items=tracking_items,
        expired_today_count=expired_count,
    )


def commit_database() -> None:
    from config import DB_PATH

    try:
        subprocess.run(
            ["git", "add", str(DB_PATH)],
            check=True,
            capture_output=True,
        )
        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if status.returncode != 0:
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"chore: update tender database {today_taipei().isoformat()}",
                ],
                check=True,
                capture_output=True,
            )
            print("Database committed to git.")
        else:
            print("Database unchanged, skip git commit.")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"Git commit skipped: {exc}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="雜波標案每日監控")
    parser.add_argument("--dry-run", action="store_true", help="不寄信，只印出摘要")
    parser.add_argument("--skip-search", action="store_true", help="跳過 API 搜尋，只用 DB 資料")
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="新案使用 OpenAI 分析（預設由 Cursor Agent 分析）",
    )
    parser.add_argument("--skip-email", action="store_true", help="不寄信（同步標案用）")
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="允許在仍有待分析標案時寄信",
    )
    parser.add_argument("--commit-db", action="store_true", help="執行後 commit database 到 git")
    parser.add_argument("--reset-db", action="store_true", help="清空既有標案與分析後再同步")
    args = parser.parse_args()

    init_db()
    today = today_taipei()
    print(f"Report date: {today.isoformat()}")
    if args.reset_db:
        cleared = reset_all_tenders()
        print(f"Reset database: cleared {cleared} row(s)")

    expired_ids = mark_expired_before(today)
    print(f"Expired today: {len(expired_ids)}")

    if not args.skip_search:
        print("Searching tenders...")
        new_count, updated_count = sync_search_results(today, use_openai=args.use_openai)
        print(f"Search done: {new_count} new, {updated_count} updated from API")
    else:
        print("Skipped API search.")

    pending = count_pending_analysis()
    if pending:
        print(f"Pending analysis: {pending} case(s)")
    if pending and not args.skip_email and not args.allow_pending:
        print("Abort: 仍有待分析標案。請先執行 Cursor Agent 分析，或加 --allow-pending")
        return 1

    summary = build_report_summary(today, len(expired_ids))
    subject = build_subject(summary)
    html = build_html(summary)

    print(
        f"Report: {len(summary.new_items)} new, "
        f"{len(summary.tracking_items)} tracking, "
        f"{summary.expired_today_count} expired"
    )

    if args.skip_email:
        print("Skipped sending email.")
    else:
        send_html_email(subject, html, dry_run=args.dry_run)

    if args.commit_db:
        commit_database()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
