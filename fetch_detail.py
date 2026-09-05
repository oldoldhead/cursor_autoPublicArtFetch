from datetime import date

from pcc_utils import (
    fetch_json,
    is_active_tender_type,
    parse_money,
    parse_roc_date,
    parse_roc_datetime,
    roc_date_str,
    tender_api_url,
    yyyymmdd_to_date,
)


def get_detail_field(detail: dict, *prefixes: str) -> str:
    for key, value in detail.items():
        if not value or "remind" in key:
            continue
        for prefix in prefixes:
            if key.endswith(prefix) or key == prefix:
                return str(value).strip()
    return ""


def get_deadline_str(detail: dict) -> str:
    return get_detail_field(
        detail,
        "領投開標:截止投標",
        "招標資料:截止投標",
        "已公告資料:截止投標",
        "採購資料:截止投標",
        "招標資料:截止投標日期",
    )


def get_budget(detail: dict) -> int | None:
    for key in ("採購資料:預算金額", "已公告資料:預算金額", "採購資料:預估金額"):
        budget = parse_money(detail.get(key))
        if budget is not None:
            return budget
    return None


def get_start_date(records: list[dict]) -> date | None:
    candidates: list[date] = []
    for record in records:
        brief_type = record.get("brief", {}).get("type", "")
        detail = record.get("detail") or {}
        dtype = detail.get("type", brief_type)
        if not is_active_tender_type(dtype):
            continue
        record_date = yyyymmdd_to_date(record.get("date", ""))
        if record_date:
            candidates.append(record_date)
    if candidates:
        return min(candidates)
    return None


def parse_bool(value) -> bool:
    return str(value).strip() in {"是", "Yes", "yes", "true", "True", "1"}


def is_expired_on(deadline_date: date | None, today: date) -> bool:
    if deadline_date is None:
        return False
    return deadline_date <= today


def fetch_tender_detail(unit_id: str, job_number: str) -> dict | None:
    data = fetch_json(tender_api_url(unit_id, job_number))
    records = data.get("records", [])
    if not records:
        return None

    latest = None
    for entry in sorted(records, key=lambda item: item.get("date", 0), reverse=True):
        if entry.get("detail"):
            latest = entry
            break
    if not latest:
        latest = records[-1]

    detail = latest.get("detail") or {}
    title = get_detail_field(detail, "採購資料:標案名稱") or latest.get("brief", {}).get("title", "")
    dtype = detail.get("type", latest.get("brief", {}).get("type", ""))
    deadline_str = get_deadline_str(detail)
    deadline_dt = parse_roc_datetime(deadline_str)
    deadline_date = deadline_dt.date() if deadline_dt else None
    start_date = get_start_date(records)

    electronic_bid = parse_bool(get_detail_field(detail, "領投開標:是否提供電子投標"))
    electronic_pickup = parse_bool(get_detail_field(detail, "領投開標:是否提供電子領標"))

    return {
        "unit_id": unit_id,
        "job_number": job_number,
        "title": title,
        "unit_name": get_detail_field(detail, "機關資料:機關名稱") or data.get("unit_name", ""),
        "budget": get_budget(detail),
        "start_date": roc_date_str(start_date),
        "start_date_iso": start_date.isoformat() if start_date else None,
        "deadline": deadline_str or "未標示",
        "deadline_date": deadline_date,
        "is_electronic_bid": electronic_bid,
        "is_electronic_pickup": electronic_pickup,
        "url": detail.get("url", ""),
        "method": get_detail_field(
            detail,
            "招標資料:招標方式",
            "採購資料:招標方式",
            "已公告資料:招標方式",
            "招標方式",
        ),
        "location": get_detail_field(
            detail,
            "其他:履約地點",
            "採購資料:履約地點（含地區）",
            "採購資料:履約地點",
            "已公告資料:履約地點（含地區）",
            "已公告資料:履約地點",
            "履約地點",
        ),
        "dtype": dtype,
    }
