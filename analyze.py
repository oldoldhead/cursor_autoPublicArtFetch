from datetime import date

from config import OPENAI_API_KEY, OPENAI_MODEL


ANALYSIS_PROMPT = """你是公共藝術／互動裝置公司「雜波」的標案顧問。
公司專長：中小型公共藝術執行、互動裝置開發、光節／光環境。
可接受公告預算：70～500 萬；截止日至少 5 天。
寫給老闆看的接案簡報，不要寫聯絡人、電話、Email、領標地址。
每個【大項】獨立一行，大項之間空一行。

請用繁體中文，依序寫：
【案件簡述】
【與雜波契合度】
【技術與履約重點】
【風險與注意事項】
【行動建議】

標案資訊：
- 標案名稱：{title}
- 機關：{unit_name}
- 預算：{budget} 元
- 招標方式：{method}
- 履約地點：{location}
- 停止受理日：{deadline}
- 距離截止日：{days_left}
"""


def format_days_left(deadline_date: date | None, today: date) -> str:
    if deadline_date is None:
        return "未標示"
    days = (deadline_date - today).days
    if days <= 0:
        return "已截止"
    return f"剩 {days} 天"


def fallback_analysis(
    title: str,
    unit_name: str,
    budget: int,
    method: str,
    location: str,
    deadline: str,
    days_left: str,
) -> str:
    fit = "中"
    if any(word in title for word in ("公共藝術", "互動裝置", "藝術裝置", "裝置藝術", "光節")):
        fit = "高"
    elif any(word in title for word in ("策展", "規劃", "行銷")):
        fit = "中"

    action = "建議下載招標文件確認履約範圍後再決定。" if days_left not in {"未標示", "已截止"} else "請先確認是否仍在等標期。"
    return (
        f"契合度：{fit}。案名與雜波業務「公共藝術／互動裝置」{'高度' if fit == '高' else '部分'}相關，"
        f"預算 {budget:,} 元、方式為 {method or '未標示'}。"
        f"履約地點：{location or '未標示'}。{action}"
    )


def analyze_tender(
    title: str,
    unit_name: str,
    budget: int,
    method: str,
    location: str,
    deadline: str,
    deadline_date: date | None,
    today: date,
) -> str:
    days_left = format_days_left(deadline_date, today)
    if not OPENAI_API_KEY:
        return fallback_analysis(title, unit_name, budget, method, location, deadline, days_left)

    prompt = ANALYSIS_PROMPT.format(
        title=title,
        unit_name=unit_name,
        budget=f"{budget:,}",
        method=method or "未標示",
        location=location or "未標示",
        deadline=deadline,
        days_left=days_left,
    )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你是專業的政府標案顧問，回答簡潔務實。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        content = response.choices[0].message.content
        return content.strip() if content else fallback_analysis(
            title, unit_name, budget, method, location, deadline, days_left
        )
    except Exception:
        return fallback_analysis(title, unit_name, budget, method, location, deadline, days_left)
