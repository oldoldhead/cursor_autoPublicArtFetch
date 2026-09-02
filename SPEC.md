# 雜波標案每日監控 — 規格確認

## 使用者設定（已確認）

| 項目 | 設定 |
|------|------|
| 執行方式 | **Cursor Automation**（雲端排程） |
| 收件信箱 | `magician.zap@gmail.com` |
| 寄信時間 | 每天 **08:00**（Asia/Taipei） |
| 移出規則 | **截止當天**移出匯報（`停止受理日 <= 今天` 不列入） |
| 緊急提醒 | **否**（主旨不加 ⚠️，不因 ≤3 天特別標示） |

## 篩選條件

- **業務**：中小型公共藝術執行、互動裝置開發
- **地區**：全台
- **預算**：公告預算 70～300 萬（不含）
- **範圍**：等標期內、尚未截止
- **排除**：已決標、已截止、誤抓（拆除、行銷、教育科技等）

## 每日匯報邏輯

```
1. 搜尋採購網（g0v PCC API）
2. 篩選高相關案件
3. 比對 SQLite：
   - 新案 → AI 分析一次 → 寫入 DB
   - 已追蹤 → 沿用 ai_analysis，只重算「距離截止日」
   - 截止日 <= 今天 → status=expired，移出匯報
4. 組裝 HTML 郵件 → SMTP 寄出
```

## 郵件欄位

每筆高相關案件含：

| 欄位 | 說明 |
|------|------|
| 標案名稱、機關、預算 | 基本資訊 |
| 起標日 | 首次招標公告日 |
| 停止受理日 | 截止投標時間 |
| **距離截止日** | 每天重算，例：「剩 6 天」 |
| 電子招標 | 電子領標 / 電子投標 |
| 連結 | 政府電子採購網 |
| AI 分析 | 新案才生成；追蹤中案件沿用首次分析 |

## 郵件分區

- **🆕 今日新增**：首次出現的高相關案件（含 AI 分析）
- **⏳ 追蹤中**：已在資料庫、尚未截止（AI 分析不重跑）
- **📊 本日摘要**：追蹤數、新增數、今日移出數

## 資料庫（SQLite）

```
tenders
├── job_number       TEXT PRIMARY KEY
├── title, unit_name, budget, start_date, deadline
├── is_electronic_bid, is_electronic_pickup, url
├── relevance_score  INTEGER
├── ai_analysis      TEXT      -- 只寫一次
├── analyzed_at      TEXT
├── first_seen       TEXT
├── status           TEXT      -- active | expired | awarded
└── last_in_report   TEXT
```

## 移出規則（截止當天）

```python
# 停止受理日為 115/09/10 17:00
# 115/09/09 → 仍在匯報（剩 1 天）
# 115/09/10 → 移出匯報（截止當天）
```

以「停止受理日的日期部分」與「今天日期」比較，不論截止時間為何，截止日當天即移出。

## 技術棧（待實作）

- Python 3.10+
- g0v PCC API（https://pcc-api.openfun.app/）
- SQLite
- OpenAI / Claude API（AI 分析）
- Gmail SMTP（magician.zap@gmail.com）
- Cursor Automation（cron `0 8 * * *`，時區 Asia/Taipei）

## 環境變數（.env，不進 git）

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=magician.zap@gmail.com
SMTP_PASS=<Gmail 應用程式密碼>
MAIL_TO=magician.zap@gmail.com
OPENAI_API_KEY=<API key>
```

## 模組結構（待實作）

```
標案自動查詢/
├── daily_report.py      # 主程式
├── search.py            # 搜尋 + 篩選
├── fetch_detail.py      # 詳細欄位
├── analyze.py           # AI 分析（僅新案）
├── database.py          # SQLite 讀寫
├── email_template.py    # HTML 模板
├── send_email.py        # SMTP
├── config.py            # 讀取 .env
├── database.db          # 執行後產生
├── .env                 # 機密（gitignore）
├── .env.example
├── requirements.txt
├── SPEC.md              # 本文件
└── AUTOMATION.md        # Cursor Automation 設定
```
