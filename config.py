import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "database.db"

load_dotenv(ROOT_DIR / ".env")

MIN_BUDGET = 700_000
MAX_BUDGET = 5_000_000
MIN_DAYS_LEFT = 5

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "magician.zap@gmail.com")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

PCC_API_BASE = "https://pcc-api.openfun.app/api"

SEARCH_KEYWORDS = [
    "公共藝術",
    "互動裝置",
    "藝術裝置",
    "裝置藝術",
    "燈光節",
    "燈光藝術",
    "數位互動",
    "文化地景",
    "光環境",
]

INCLUDE_KEYWORDS = SEARCH_KEYWORDS + ["互動體驗", "設置計畫", "展示製作"]

CORE_KEYWORDS = ["公共藝術", "互動裝置", "藝術裝置", "裝置藝術", "光節", "燈光節", "數位互動", "光環境"]

HARD_EXCLUDE_KEYWORDS = [
    "清潔",
    "保全",
    "維護保養",
    "電視牆",
    "雷達",
    "反響板",
    "交通接駁",
    "遊覽車",
    "印刷",
    "清運",
    "修繕工程",
    "水電",
    "空調",
    "電梯",
    "資訊系統維護",
    "採購案維護",
    "綠美化維護",
    "圍牆補照",
    "拆除",
    "教室系統",
    "文物修護",
    "指標系統",
    "環境改善工程",
    "馬拉松",
    "路跑",
]

SOFT_EXCLUDE_KEYWORDS = [
    "宣傳行銷",
    "票券代售",
    "觀光節",
    "美食節",
    "購物節",
    "嘉年華",
]
