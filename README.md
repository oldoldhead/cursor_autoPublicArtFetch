# 雜波標案每日監控

自動搜尋 [政府電子採購網](https://web.pcc.gov.tw/pis/) 高相關標案，每日寄送 HTML 郵件。

**標案分析由 Cursor Cloud Agent 完成（方案 B），不需 OpenAI API key。**

## 快速開始

```powershell
python -m pip install -r requirements.txt
copy .env.example .env
# 編輯 .env：只需 SMTP 設定
```

### 本機完整流程

```powershell
python daily_report.py --skip-email    # 1. 同步標案
python list_pending.py                 # 2. 看待分析清單
# 3. Cursor Agent 或手動寫分析
python update_analysis.py --tender-id "unit:job" --analysis "..."
python daily_report.py --skip-search   # 4. 寄信
```

### 排程

見 [AUTOMATION.md](./AUTOMATION.md) — 在 cursor.com/automations 設定每天 08:00。

## 模組

| 檔案 | 用途 |
|------|------|
| `daily_report.py` | 主程式（搜尋 / 寄信） |
| `list_pending.py` | 匯出待 Cursor 分析的標案 |
| `update_analysis.py` | 寫入 Agent 分析結果 |
| `data/database.db` | 標案追蹤資料庫 |

## 命令列

| 參數 | 說明 |
|------|------|
| `--skip-email` | 只同步標案，不寄信 |
| `--skip-search` | 只用 DB 資料寄信 |
| `--allow-pending` | 待分析案件未完成仍寄信 |
| `--use-openai` | 改用 OpenAI 分析（選用） |
| `--commit-db` | commit database 到 git |
