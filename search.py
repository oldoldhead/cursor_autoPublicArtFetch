from dataclasses import dataclass, field
from datetime import date

from config import (
    CORE_KEYWORDS,
    HARD_EXCLUDE_KEYWORDS,
    INCLUDE_KEYWORDS,
    MAX_BUDGET,
    MIN_BUDGET,
    MIN_DAYS_LEFT,
    SEARCH_KEYWORDS,
    SOFT_EXCLUDE_KEYWORDS,
)
from fetch_detail import fetch_tender_detail, is_expired_on
from pcc_utils import fetch_json, is_active_tender_type, search_api_url, today_taipei
import time


@dataclass
class SearchHit:
    unit_id: str
    job_number: str
    title: str
    unit_name: str
    brief_type: str
    matched_keywords: list[str] = field(default_factory=list)


def matches_core_keyword(title: str) -> bool:
    for word in CORE_KEYWORDS:
        if word not in title:
            continue
        if word == "光節" and "觀光節" in title:
            if not any(x in title for x in ["燈光", "裝置", "藝術", "光影"]):
                continue
        return True
    return False


def is_relevant_title(title: str) -> bool:
    if any(word in title for word in HARD_EXCLUDE_KEYWORDS):
        return False
    has_core = matches_core_keyword(title)
    if not has_core and any(word in title for word in SOFT_EXCLUDE_KEYWORDS):
        return False
    return any(word in title for word in INCLUDE_KEYWORDS)


def score_title(title: str) -> int:
    score = 0
    if matches_core_keyword(title):
        score += 2
    for word in INCLUDE_KEYWORDS:
        if word in title and word not in CORE_KEYWORDS:
            score += 1
    return score


def is_high_relevance(title: str, score: int) -> bool:
    if matches_core_keyword(title):
        return True
    return score >= 2


def search_keyword(query: str, max_pages: int = 1) -> list[dict]:
    results: list[dict] = []
    for page in range(1, max_pages + 1):
        try:
            data = fetch_json(search_api_url(query, page))
        except Exception as exc:
            print(f"  搜尋「{query}」失敗: {exc}", flush=True)
            break
        records = data.get("records", [])
        if not records:
            break
        results.extend(records)
        if page >= data.get("total_pages", 1):
            break
        time.sleep(0.5)
    return results


def collect_search_hits() -> dict[str, SearchHit]:
    seen: dict[str, SearchHit] = {}
    for keyword in SEARCH_KEYWORDS:
        print(f"  關鍵字: {keyword}", flush=True)
        for record in search_keyword(keyword):
            title = record.get("brief", {}).get("title", "")
            brief_type = record.get("brief", {}).get("type", "")
            if not is_active_tender_type(brief_type):
                continue
            if not is_relevant_title(title):
                continue
            score = score_title(title)
            if not is_high_relevance(title, score):
                continue

            key = f"{record['unit_id']}:{record['job_number']}"
            if key not in seen:
                seen[key] = SearchHit(
                    unit_id=record["unit_id"],
                    job_number=record["job_number"],
                    title=title,
                    unit_name=record.get("unit_name", ""),
                    brief_type=brief_type,
                    matched_keywords=[keyword],
                )
            elif keyword not in seen[key].matched_keywords:
                seen[key].matched_keywords.append(keyword)
        time.sleep(1.0)
    return seen


def find_high_relevance_tenders(today: date | None = None) -> list[dict]:
    today = today or today_taipei()
    hits = collect_search_hits()
    print(f"  候選標案: {len(hits)} 筆，開始取詳細資料...", flush=True)
    results: list[dict] = []

    for index, hit in enumerate(hits.values(), 1):
        if index % 10 == 0:
            print(f"  處理中 {index}/{len(hits)}...", flush=True)
        try:
            detail = fetch_tender_detail(hit.unit_id, hit.job_number)
        except Exception as exc:
            print(f"  略過 {hit.job_number}: {exc}", flush=True)
            continue
        time.sleep(1.2)

        if not detail:
            continue
        if not is_active_tender_type(detail["dtype"]):
            continue
        if detail["budget"] is None or not (MIN_BUDGET <= detail["budget"] <= MAX_BUDGET):
            continue
        if is_expired_on(detail["deadline_date"], today):
            continue
        deadline_date = detail["deadline_date"]
        if deadline_date is None or (deadline_date - today).days < MIN_DAYS_LEFT:
            continue

        score = score_title(detail["title"])
        if not is_high_relevance(detail["title"], score):
            continue

        results.append(
            {
                **detail,
                "relevance_score": score,
                "matched_keywords": ", ".join(hit.matched_keywords),
            }
        )

    results.sort(key=lambda item: (item["deadline_date"] or date.max, -item["budget"]))
    return results
