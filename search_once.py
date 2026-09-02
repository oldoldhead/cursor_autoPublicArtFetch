import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

TODAY = date(2026, 9, 2)
MIN_BUDGET = 700_000
MAX_BUDGET = 3_000_000
KEYWORDS = [
    "公共藝術",
    "互動裝置",
    "藝術裝置",
    "光節",
    "燈光節",
    "燈光藝術",
    "展演裝置",
    "數位藝術",
    "戶外裝置",
    "沉浸式",
    "策展",
]


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_money(value) -> int | None:
    if not value:
        return None
    text = str(value).replace(",", "").replace("元", "").replace("新台幣", "").strip()
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def parse_roc_date(value) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    match = re.search(r"(\d{2,3})[\/年](\d{1,2})[\/月](\d{1,2})", text)
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if year < 200:
        year += 1911
    try:
        return date(year, month, day)
    except ValueError:
        return None


def is_active_tender_type(text: str) -> bool:
    return any(keyword in text for keyword in ("招標", "公開取得", "公開閱覽", "公開徵求"))


def search_keyword(query: str, max_pages: int = 3) -> list[dict]:
    results = []
    for page in range(1, max_pages + 1):
        url = (
            "https://pcc-api.openfun.app/api/searchbytitle?query="
            f"{urllib.parse.quote(query)}&page={page}"
        )
        try:
            data = fetch_json(url)
        except Exception:
            break
        records = data.get("records", [])
        if not records:
            break
        results.extend(records)
        if page >= data.get("total_pages", 1):
            break
        time.sleep(0.2)
    return results


def get_deadline(detail: dict) -> str:
    for key in (
        "招標資料:截止投標",
        "已公告資料:截止投標",
        "採購資料:截止投標",
        "招標資料:截止投標日期",
    ):
        if detail.get(key):
            return detail[key]
    return ""


def get_budget(detail: dict) -> int | None:
    for key in ("採購資料:預算金額", "已公告資料:預算金額", "採購資料:預估金額"):
        budget = parse_money(detail.get(key))
        if budget is not None:
            return budget
    return None


def main() -> None:
    seen: dict[tuple[str, str], dict] = {}
    for keyword in KEYWORDS:
        print(f"搜尋關鍵字: {keyword}...", file=sys.stderr)
        for record in search_keyword(keyword):
            key = (record["unit_id"], record["job_number"])
            if key not in seen:
                seen[key] = {"record": record, "keywords": [keyword]}
            elif keyword not in seen[key]["keywords"]:
                seen[key]["keywords"].append(keyword)

    print(f"共找到 {len(seen)} 筆不重複標案，開始篩選...", file=sys.stderr)

    matches = []
    checked = 0
    for (unit_id, job_number), item in seen.items():
        record = item["record"]
        brief_type = record.get("brief", {}).get("type", "")
        title = record.get("brief", {}).get("title", "")
        if not is_active_tender_type(brief_type):
            continue

        checked += 1
        try:
            detail_data = fetch_json(
                "https://pcc-api.openfun.app/api/tender?"
                f"unit_id={urllib.parse.quote(unit_id)}&job_number={urllib.parse.quote(job_number)}"
            )
        except Exception:
            continue
        time.sleep(0.15)

        records = detail_data.get("records", [])
        if not records:
            continue

        latest = None
        for entry in sorted(records, key=lambda x: x.get("date", 0), reverse=True):
            if entry.get("detail"):
                latest = entry
                break
        if not latest:
            latest = records[-1]

        detail = latest.get("detail", {})
        dtype = detail.get("type", brief_type)
        if not is_active_tender_type(dtype):
            continue

        budget = get_budget(detail)
        if budget is None or budget < MIN_BUDGET or budget > MAX_BUDGET:
            continue

        deadline_str = get_deadline(detail)
        deadline = parse_roc_date(deadline_str)
        if deadline and deadline < TODAY:
            continue

        pcc_url = detail.get("url", "")
        matches.append(
            {
                "title": detail.get("採購資料:標案名稱") or title,
                "unit": detail.get("機關資料:機關名稱") or record.get("unit_name", ""),
                "budget": budget,
                "deadline": deadline_str or "未標示",
                "deadline_date": str(deadline) if deadline else "",
                "type": dtype,
                "location": detail.get("採購資料:履約地點（含地區）")
                or detail.get("採購資料:履約地點")
                or "",
                "method": detail.get("採購資料:招標方式") or "",
                "keywords": ", ".join(item["keywords"]),
                "job_number": job_number,
                "url": pcc_url,
            }
        )

    matches.sort(key=lambda x: (x["deadline_date"] or "9999", -x["budget"]))

    print(f"\n篩選完成：檢查 {checked} 筆招標類公告，符合條件 {len(matches)} 筆\n")
    print("=" * 80)
    for index, match in enumerate(matches, 1):
        print(f"【{index}】{match['title']}")
        print(f"  機關：{match['unit']}")
        print(f"  預算：{match['budget']:,} 元")
        print(f"  截止投標：{match['deadline']}")
        print(f"  履約地點：{match['location']}")
        print(f"  招標方式：{match['method']}")
        print(f"  公告類型：{match['type']}")
        print(f"  命中關鍵字：{match['keywords']}")
        print(f"  案號：{match['job_number']}")
        if match["url"]:
            print(f"  連結：{match['url']}")
        print()


if __name__ == "__main__":
    main()
