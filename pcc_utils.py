import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

from config import PCC_API_BASE

TAIPEI = ZoneInfo("Asia/Taipei")


def today_taipei() -> date:
    return datetime.now(TAIPEI).date()


_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://pcc-api.openfun.app/",
}


def fetch_json(url: str, retries: int = 4) -> dict | list:
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HTTP_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            err = str(exc)
            wait = 3 * (attempt + 1)
            if "429" in err:
                wait = 8 * (attempt + 1)
            if attempt < retries - 1:
                time.sleep(wait)
    raise last_error  # type: ignore[misc]


def parse_money(value) -> int | None:
    if not value:
        return None
    text = str(value).replace(",", "").replace("元", "").replace("新台幣", "").strip()
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def parse_roc_datetime(value) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    match = re.search(
        r"(\d{2,3})[\/年](\d{1,2})[\/月](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?",
        text,
    )
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if year < 200:
        year += 1911
    hour = int(match.group(4)) if match.group(4) else 0
    minute = int(match.group(5)) if match.group(5) else 0
    try:
        return datetime(year, month, day, hour, minute, tzinfo=TAIPEI)
    except ValueError:
        return None


def parse_roc_date(value) -> date | None:
    dt = parse_roc_datetime(value)
    return dt.date() if dt else None


def roc_date_str(value: date | None) -> str:
    if not value:
        return "未標示"
    roc_year = value.year - 1911
    return f"{roc_year:03d}/{value.month:02d}/{value.day:02d}"


def yyyymmdd_to_date(value: int | str) -> date | None:
    text = str(value)
    if len(text) != 8:
        return None
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def is_active_tender_type(text: str) -> bool:
    if any(x in text for x in ("決標", "定期彙送", "無法決標")):
        return False
    return any(keyword in text for keyword in ("招標", "公開取得", "公開閱覽", "公開徵求"))


def tender_api_url(unit_id: str, job_number: str) -> str:
    return (
        f"{PCC_API_BASE}/tender?"
        f"unit_id={urllib.parse.quote(unit_id)}&job_number={urllib.parse.quote(job_number)}"
    )


def search_api_url(query: str, page: int = 1) -> str:
    return (
        f"{PCC_API_BASE}/searchbytitle?"
        f"query={urllib.parse.quote(query)}&page={page}"
    )
