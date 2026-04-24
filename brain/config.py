"""
后稷项目全局配置
所有硬件参数、路径、阈值、API Key 均在此集中管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件（brain/ 的上一层）
load_dotenv(Path(__file__).parent.parent / ".env")

# ── 项目根路径 ──────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
RAG_STORE_DIR = DATA_DIR / "rag_store"

# 确保运行时目录存在
DATA_DIR.mkdir(exist_ok=True)
SNAPSHOT_DIR.mkdir(exist_ok=True)
RAG_STORE_DIR.mkdir(exist_ok=True)

# ── SQLite 数据库 ────────────────────────────────────────
DB_PATH = DATA_DIR / "houji.db"

# ── AI 思考日志 ──────────────────────────────────────────
THOUGHT_LOG_PATH = DATA_DIR / "thought.log"

# ── 串口通信（Pi5 ↔ Pico）───────────────────────────────
SERIAL_PORT = "/dev/ttyACM0"   # Pico 连接的串口设备
SERIAL_BAUD = 115200

# ── Gemini API ───────────────────────────────────────────
# ⚠️ API Key 请通过环境变量注入，不要硬编码在此处
# 在 Pi5 上执行: export GEMINI_API_KEY="your_new_key"
# 或写入 ~/.bashrc 永久生效
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"  # 最新 Flash 预览版
GEMINI_PRO_MODEL   = "gemini-3-pro-preview"    # 最新 Pro 预览版

# ── 采集与决策间隔（秒）─────────────────────────────────
SENSOR_INTERVAL   = 60     # 传感器采集频率
SNAPSHOT_INTERVAL = 300    # 摄像头快照频率
AI_DECISION_INTERVAL = 300 # AI 决策频率

# ── 生长环境阈值 ─────────────────────────────────────────
ENV_THRESHOLDS = {
    "temp_min": 18.0,   # 最低温度 (°C)
    "temp_max": 28.0,   # 最高温度 (°C)
    "humidity_min": 60, # 最低湿度 (%)
    "ph_min": 5.5,      # pH 下限
    "ph_max": 6.5,      # pH 上限
    "ec_min": 1000.0,   # EC 下限 (μS/cm)
    "ec_max": 2000.0,   # EC 上限 (μS/cm)
}

# ── 光照计划（24小时制）─────────────────────────────────
LIGHT_ON_HOUR  = 6   # 开灯时间
LIGHT_OFF_HOUR = 22  # 关灯时间
