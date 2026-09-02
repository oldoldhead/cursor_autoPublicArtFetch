import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

from config import DB_PATH, DATA_DIR
from pcc_utils import TAIPEI


@dataclass
class TenderRow:
    tender_id: str
    unit_id: str
    job_number: str
    title: str
    unit_name: str
    budget: int
    start_date: str | None
    deadline: str | None
    deadline_date: date | None
    is_electronic_bid: bool
    is_electronic_pickup: bool
    url: str
    method: str
    location: str
    relevance_score: int
    matched_keywords: str
    ai_analysis: str | None
    analyzed_at: str | None
    first_seen: str
    status: str
    last_in_report: str | None


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tenders (
                tender_id TEXT PRIMARY KEY,
                unit_id TEXT NOT NULL,
                job_number TEXT NOT NULL,
                title TEXT NOT NULL,
                unit_name TEXT NOT NULL,
                budget INTEGER NOT NULL,
                start_date TEXT,
                deadline TEXT,
                deadline_date TEXT,
                is_electronic_bid INTEGER NOT NULL DEFAULT 0,
                is_electronic_pickup INTEGER NOT NULL DEFAULT 0,
                url TEXT,
                method TEXT,
                location TEXT,
                relevance_score INTEGER NOT NULL DEFAULT 0,
                matched_keywords TEXT,
                ai_analysis TEXT,
                analyzed_at TEXT,
                first_seen TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                last_in_report TEXT
            )
            """
        )
        conn.commit()


def make_tender_id(unit_id: str, job_number: str) -> str:
    return f"{unit_id}:{job_number}"


def get_tender(tender_id: str) -> TenderRow | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM tenders WHERE tender_id = ?", (tender_id,)
        ).fetchone()
    return _row_to_tender(row) if row else None


def list_active_tenders() -> list[TenderRow]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tenders WHERE status = 'active' ORDER BY deadline_date ASC, budget DESC"
        ).fetchall()
    return [_row_to_tender(row) for row in rows]


def upsert_tender(row: TenderRow) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO tenders (
                tender_id, unit_id, job_number, title, unit_name, budget,
                start_date, deadline, deadline_date,
                is_electronic_bid, is_electronic_pickup,
                url, method, location, relevance_score, matched_keywords,
                ai_analysis, analyzed_at, first_seen, status, last_in_report
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tender_id) DO UPDATE SET
                title = excluded.title,
                unit_name = excluded.unit_name,
                budget = excluded.budget,
                start_date = excluded.start_date,
                deadline = excluded.deadline,
                deadline_date = excluded.deadline_date,
                is_electronic_bid = excluded.is_electronic_bid,
                is_electronic_pickup = excluded.is_electronic_pickup,
                url = excluded.url,
                method = excluded.method,
                location = excluded.location,
                relevance_score = excluded.relevance_score,
                matched_keywords = excluded.matched_keywords,
                ai_analysis = COALESCE(tenders.ai_analysis, excluded.ai_analysis),
                analyzed_at = COALESCE(tenders.analyzed_at, excluded.analyzed_at),
                status = excluded.status,
                last_in_report = excluded.last_in_report
            """,
            (
                row.tender_id,
                row.unit_id,
                row.job_number,
                row.title,
                row.unit_name,
                row.budget,
                row.start_date,
                row.deadline,
                row.deadline_date.isoformat() if row.deadline_date else None,
                int(row.is_electronic_bid),
                int(row.is_electronic_pickup),
                row.url,
                row.method,
                row.location,
                row.relevance_score,
                row.matched_keywords,
                row.ai_analysis,
                row.analyzed_at,
                row.first_seen,
                row.status,
                row.last_in_report,
            ),
        )
        conn.commit()


def mark_expired_before(today: date) -> list[str]:
    today_iso = today.isoformat()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT tender_id, title FROM tenders
            WHERE status = 'active'
              AND deadline_date IS NOT NULL
              AND deadline_date <= ?
            """,
            (today_iso,),
        ).fetchall()
        expired_ids = [row["tender_id"] for row in rows]
        if expired_ids:
            conn.execute(
                """
                UPDATE tenders SET status = 'expired'
                WHERE status = 'active'
                  AND deadline_date IS NOT NULL
                  AND deadline_date <= ?
                """,
                (today_iso,),
            )
            conn.commit()
    return expired_ids


def _row_to_tender(row: sqlite3.Row) -> TenderRow:
    deadline_date = None
    if row["deadline_date"]:
        deadline_date = date.fromisoformat(row["deadline_date"])
    return TenderRow(
        tender_id=row["tender_id"],
        unit_id=row["unit_id"],
        job_number=row["job_number"],
        title=row["title"],
        unit_name=row["unit_name"],
        budget=row["budget"],
        start_date=row["start_date"],
        deadline=row["deadline"],
        deadline_date=deadline_date,
        is_electronic_bid=bool(row["is_electronic_bid"]),
        is_electronic_pickup=bool(row["is_electronic_pickup"]),
        url=row["url"] or "",
        method=row["method"] or "",
        location=row["location"] or "",
        relevance_score=row["relevance_score"],
        matched_keywords=row["matched_keywords"] or "",
        ai_analysis=row["ai_analysis"],
        analyzed_at=row["analyzed_at"],
        first_seen=row["first_seen"],
        status=row["status"],
        last_in_report=row["last_in_report"],
    )


def list_pending_analysis() -> list[TenderRow]:
    """列出 active 且尚未有 AI 分析的標案。"""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tenders
            WHERE status = 'active'
              AND (ai_analysis IS NULL OR ai_analysis = '')
            ORDER BY first_seen DESC, deadline_date ASC
            """
        ).fetchall()
    return [_row_to_tender(row) for row in rows]


def set_analysis(tender_id: str, analysis: str) -> bool:
    """寫入 Cursor Agent 產生的分析。成功回傳 True。"""
    analysis = analysis.strip()
    if not analysis:
        return False
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE tenders
            SET ai_analysis = ?, analyzed_at = ?
            WHERE tender_id = ? AND status = 'active'
            """,
            (analysis, now_iso(), tender_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def count_pending_analysis() -> int:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM tenders
            WHERE status = 'active'
              AND (ai_analysis IS NULL OR ai_analysis = '')
            """
        ).fetchone()
    return int(row["cnt"]) if row else 0
