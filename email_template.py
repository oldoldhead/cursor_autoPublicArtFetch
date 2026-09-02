from dataclasses import dataclass
from datetime import date

from analyze import format_days_left
from database import TenderRow
from pcc_utils import roc_date_str


@dataclass
class ReportSummary:
    report_date: date
    new_items: list[TenderRow]
    tracking_items: list[TenderRow]
    expired_today_count: int


def _electronic_label(pickup: bool, bid: bool) -> str:
    pickup_text = "電子領標 ✅" if pickup else "電子領標 ❌"
    bid_text = "電子投標 ✅" if bid else "電子投標 ❌"
    return f"{pickup_text}｜{bid_text}"


def _render_tender_block(item: TenderRow, today: date, show_new_badge: bool) -> str:
    badge = '<span style="color:#2563eb;font-weight:bold;">🆕 今日新增</span><br>' if show_new_badge else ""
    days_left = format_days_left(item.deadline_date, today)
    analyzed_label = item.analyzed_at[:10] if item.analyzed_at else "未知"

    return f"""
    <div style="margin-bottom:28px;padding:16px;border:1px solid #e5e7eb;border-radius:8px;">
      {badge}
      <h3 style="margin:0 0 12px;font-size:18px;">{item.title}</h3>
      <table style="border-collapse:collapse;width:100%;font-size:14px;">
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;width:120px;">機關</td><td>{item.unit_name}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">預算</td><td>{item.budget:,} 元</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">起標日</td><td>{item.start_date or "未標示"}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">停止受理日</td><td>{item.deadline or "未標示"}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">距離截止日</td><td><strong>{days_left}</strong></td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">履約地點</td><td>{item.location or "未標示"}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">招標方式</td><td>{item.method or "未標示"}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">電子招標</td><td>{_electronic_label(item.is_electronic_pickup, item.is_electronic_bid)}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">案號</td><td>{item.job_number}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#6b7280;">連結</td><td><a href="{item.url}">查看標案</a></td></tr>
      </table>
      <p style="margin:14px 0 4px;font-size:14px;"><strong>🤖 AI 分析</strong>
        <span style="color:#6b7280;">（{analyzed_label} 分析{"" if show_new_badge else "，未重跑"}）</span>
      </p>
      <p style="margin:0;font-size:14px;line-height:1.6;">{item.ai_analysis or "（尚無分析）"}</p>
    </div>
    """


def build_subject(summary: ReportSummary) -> str:
    date_text = summary.report_date.strftime("%Y/%m/%d")
    return (
        f"[雜波標案日報] {date_text} — "
        f"追蹤中 {len(summary.tracking_items) + len(summary.new_items)} 筆｜"
        f"新增 {len(summary.new_items)} 筆"
    )


def build_html(summary: ReportSummary) -> str:
    today = summary.report_date
    date_label = f"{today.year} 年 {today.month:02d} 月 {today.day:02d} 日"
    weekday = "一二三四五六日"[today.weekday()]
    total = len(summary.new_items) + len(summary.tracking_items)

    new_html = "".join(_render_tender_block(item, today, True) for item in summary.new_items)
    tracking_html = "".join(_render_tender_block(item, today, False) for item in summary.tracking_items)

    if not new_html:
        new_html = '<p style="color:#6b7280;">今日無新增高相關案件。</p>'
    if not tracking_html:
        tracking_html = '<p style="color:#6b7280;">目前無其他追蹤中案件。</p>'

    return f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head><meta charset="UTF-8"></head>
    <body style="font-family:'Segoe UI',Arial,sans-serif;color:#111827;max-width:760px;margin:0 auto;padding:24px;">
      <h1 style="font-size:22px;margin-bottom:4px;">📋 雜波標案每日監控報告</h1>
      <p style="color:#6b7280;margin-top:0;">
        {date_label}（週{weekday}）
      </p>
      <p style="font-size:14px;">
        篩選：公共藝術／互動裝置｜預算 70～300 萬｜等標期內（截止當天移出）
      </p>

      <h2 style="font-size:18px;margin-top:28px;">🆕 今日新增（{len(summary.new_items)} 筆）</h2>
      {new_html}

      <h2 style="font-size:18px;margin-top:28px;">⏳ 追蹤中（{len(summary.tracking_items)} 筆）</h2>
      {tracking_html}

      <h2 style="font-size:18px;margin-top:28px;">📊 本日摘要</h2>
      <table style="border-collapse:collapse;font-size:14px;">
        <tr><td style="padding:4px 16px 4px 0;color:#6b7280;">追蹤中案件</td><td>{total} 筆</td></tr>
        <tr><td style="padding:4px 16px 4px 0;color:#6b7280;">今日新增</td><td>{len(summary.new_items)} 筆</td></tr>
        <tr><td style="padding:4px 16px 4px 0;color:#6b7280;">今日移出（已截止）</td><td>{summary.expired_today_count} 筆</td></tr>
      </table>

      <p style="margin-top:32px;font-size:12px;color:#9ca3af;">
        資料來源：<a href="https://web.pcc.gov.tw/pis/">政府電子採購網</a>（via g0v PCC API）｜自動寄送，請以官方公告為準
      </p>
    </body>
    </html>
    """
