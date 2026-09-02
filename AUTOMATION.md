# Cursor Automation 設定指南（方案 B：Cursor Agent 分析）

標案分析由 **Cursor Cloud Agent** 完成，使用 Cursor 訂閱額度，**不需 OpenAI API key**。

---

## 流程概覽

```
08:00 觸發 Automation
  │
  ├─ 步驟 1  python daily_report.py --skip-email     搜尋標案、更新 DB
  ├─ 步驟 2  python list_pending.py                 匯出待分析清單
  ├─ 步驟 3  Cursor Agent 逐案分析                   寫入 DB
  ├─ 步驟 4  python daily_report.py --skip-search   寄出 HTML 郵件
  └─ 步驟 5  git commit data/database.db
```

---

## 前置條件（缺一不可）

1. Cursor **Pro** 以上（Automations + Cloud Agent）
2. **本專案已是 Git repo，並 push 到 GitHub**（否則 Automation 會在空工作區啟動）
3. Cursor GitHub App 已授權該 repo（All 或 Selected 有勾到）
4. Automation 設定裡 **Repository 有選到這個 repo**（不是 No repository）
5. SMTP 用 Cursor Secrets 設定（`.env` 不要 commit）

### 若錯誤是「空工作區 / repoUrl 為空」

代表自動化沒綁倉庫。請依序：

1. 本機 `git init` → push 到 GitHub  
2. GitHub → Settings → Applications → Cursor → Configure → 勾選該 repo  
3. 編輯 Automation → Repository 選該 repo → Save  
4. 手動 Run once 驗證

---

## 建立 Automation

1. 前往 [cursor.com/automations](https://cursor.com/automations)
2. **New Automation**
3. 設定：

| 項目 | 值 |
|------|-----|
| Name | 雜波標案每日監控 |
| Trigger | Scheduled |
| Cron | `0 8 * * *` |
| Timezone | Asia/Taipei |
| Repository | 本專案 repo |

4. **Instructions** — 完整貼上：

```
你是雜波公司的標案顧問 Agent。雜波專長：中小型公共藝術執行、互動裝置、光節，預算 70～300 萬。

每次觸發依序執行，不可跳步：

━━━ 步驟 1：同步標案 ━━━
pip install -r requirements.txt
python daily_report.py --skip-email --commit-db

━━━ 步驟 2：匯出待分析清單 ━━━
python list_pending.py
讀取 data/pending_analysis.json

━━━ 步驟 3：分析每一筆待分析標案 ━━━
若 count 為 0，跳至步驟 4。

對 pending_analysis.json 中每一筆 tenders，撰寫繁體中文結構化分析，包含：
【案件簡述】2～3 句
【與雜波契合度】高/中/低 + 理由
【技術與履約重點】可能工作內容、是否需評選/企劃書
【風險與注意事項】預算、時程、門檻
【行動建議】是否建議投標、第一步

寫入資料庫（每案一行）：
python update_analysis.py --tender-id "<tender_id>" --analysis "<分析全文>"

注意：分析只寫一次，已分析過的案件不要重跑。

━━━ 步驟 4：寄出日報 ━━━
python daily_report.py --skip-search --commit-db

━━━ 完成 ━━━
回報：新增幾筆、分析幾筆、追蹤中幾筆、是否寄信成功。
若任一步失敗，說明錯誤。
```

5. Save & Activate

---

## 本機測試（模擬 Automation）

```powershell
# 步驟 1：同步標案（不寄信）
python daily_report.py --skip-email

# 步驟 2：看有哪些待分析
python list_pending.py

# 步驟 3：手動寫入分析（或用 Cursor Chat 幫你分析後貼上）
python update_analysis.py --tender-id "3.76.60.30:115A35" --file analysis.txt

# 步驟 4：寄信
python daily_report.py --skip-search
```

---

## 輔助指令

| 指令 | 用途 |
|------|------|
| `python daily_report.py --skip-email` | 只搜尋 + 更新 DB |
| `python list_pending.py` | 匯出 `data/pending_analysis.json` |
| `python update_analysis.py --tender-id X --analysis "..."` | 寫入分析 |
| `python daily_report.py --skip-search` | 從 DB 組信並寄出 |
| `python daily_report.py --skip-search --allow-pending` | 允許待分析案件仍寄信 |

---

## Secrets 設定

`.env` 不要 commit。Automation 需在 Cursor 設定環境變數：

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
MAIL_TO=magician.zap@gmail.com
```

---

## 常見問題

| 問題 | 解法 |
|------|------|
| 寄信失敗 | 檢查 SMTP secrets |
| 分析重複 | DB 已有 ai_analysis 的案子不會出現在 pending |
| 截止當天仍出現 | 停止受理日 <= 今天會標記 expired |
| 待分析未完成的寄信 | 預設會 abort；完成步驟 3 或加 `--allow-pending` |
