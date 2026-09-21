"""
后稷项目全局配置
所有硬件参数、路径、阈值、API Key 均在此集中管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from crop_profiles import get_crop_profile, get_growth_stage

# 自动加载项目根目录的 .env 文件（brain/ 的上一层）
load_dotenv(Path(__file__).parent.parent / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))

# ── 项目与实例路径 ────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
INSTANCE_ID = os.getenv("HOUJI_INSTANCE_ID", "tomato-01").strip()

_data_dir = Path(os.getenv("HOUJI_DATA_DIR", str(BASE_DIR / "data"))).expanduser()
if not _data_dir.is_absolute():
    _data_dir = PROJECT_ROOT / _data_dir
DATA_DIR = _data_dir.resolve()
SNAPSHOT_DIR = DATA_DIR / "snapshots"

# 确保运行时目录存在
DATA_DIR.mkdir(exist_ok=True)
SNAPSHOT_DIR.mkdir(exist_ok=True)

# ── SQLite 数据库 ────────────────────────────────────────
DB_PATH = DATA_DIR / "houji.db"

# ── AI 思考日志 ──────────────────────────────────────────
THOUGHT_LOG_PATH = DATA_DIR / "thought.log"

# ── 硬件连接 ──────────────────────────────────────────────
# Pico 优先使用稳定的 /dev/serial/by-id 路径；UART 环境传感器独立配置。
SERIAL_PORT = os.getenv(
    "PICO_SERIAL_PORT",
    "/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e99114e1a06febe0-if00",
)
SERIAL_BAUD = _env_int("PICO_SERIAL_BAUD", 115200)
AIR_SENSOR_PORT = os.getenv("AIR_SENSOR_PORT", "/dev/ttyAMA0")
AIR_SENSOR_BAUD = _env_int("AIR_SENSOR_BAUD", 9600)
CAMERA_INDEX = _env_int("CAMERA_INDEX", 0)
TDS_COMPENSATION_TEMPERATURE_C = _env_float("TDS_COMPENSATION_TEMPERATURE_C", 25.0)

# ── 阿里云百炼千问 API ───────────────────────────────────
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.7-plus")

# ── 作物与营养液配置 ──────────────────────────────────────
# 当前默认采用用户提供的“瓜果专用营养液 A+B”番茄标签。
# GROWTH_STAGE 是首次启动兜底；manual 模式时为人工覆盖。
CROP_PROFILE_NAME = os.getenv("CROP_PROFILE", "tomato_fruit_ab").strip().lower()
GROWTH_STAGE = os.getenv("GROWTH_STAGE", "seedling").strip().lower()
GROWTH_STAGE_MODE = os.getenv("GROWTH_STAGE_MODE", "auto").strip().lower()
if GROWTH_STAGE_MODE not in {"auto", "manual"}:
    raise ValueError("GROWTH_STAGE_MODE 只能是 auto 或 manual")
GROWTH_STATE_PATH = DATA_DIR / "growth_state.json"
CROP_PROFILE = get_crop_profile(CROP_PROFILE_NAME)
CURRENT_GROWTH_STAGE = get_growth_stage(CROP_PROFILE, GROWTH_STAGE)

CROP_NAME = CROP_PROFILE["crop_name"]
NUTRIENT_PRODUCT = CROP_PROFILE["nutrient_product"]
EC_TARGETS = CROP_PROFILE["ec_targets"]
EC_TARGET_MIN = CURRENT_GROWTH_STAGE["min"]
EC_TARGET_MAX = CURRENT_GROWTH_STAGE["max"]

# A/B 两液的实际投加管路尚未确认，默认禁止自动启动营养液泵。
NUTRIENT_DOSING_ENABLED = _env_bool("NUTRIENT_DOSING_ENABLED", False)

# ── 运行模式与功能开关 ────────────────────────────────────
RUN_MODE = os.getenv("RUN_MODE", "observe").strip().lower()
if RUN_MODE not in {"observe", "control"}:
    raise ValueError("RUN_MODE 只能是 observe 或 control")

CONTROL_ENABLED = RUN_MODE == "control"
AI_ENABLED = _env_bool("AI_ENABLED", False)
CAMERA_ENABLED = _env_bool("CAMERA_ENABLED", True)
CAMERA_FLASH_ENABLED = _env_bool("CAMERA_FLASH_ENABLED", False)

# ── 采集与决策间隔（秒）─────────────────────────────────
SENSOR_INTERVAL = _env_int("SENSOR_INTERVAL", 10)
SNAPSHOT_INTERVAL = _env_int("SNAPSHOT_INTERVAL", 1800)
AI_DECISION_INTERVAL = _env_int("AI_DECISION_INTERVAL", 1800)


# ── 光照计划（24小时制）─────────────────────────────────
LIGHT_ON_HOUR  = 6   # 开灯时间
LIGHT_OFF_HOUR = 22  # 关灯时间

# ── 种植批次与周期跟踪 ──────────────────────────────────
PLANTING_BATCH = os.getenv("PLANTING_BATCH", "TOMATO-2026-08-12-A")
PLANTING_START_DATE = os.getenv("PLANTING_START_DATE", "2026-08-12")
