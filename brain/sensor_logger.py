"""
传感器数据采集与 SQLite 存储
表结构：
  sensor_readings(id, timestamp, temp, humidity, co2, ch2o, tvoc, pm25, pm10, ec, ph)
  ec 字段由 TDS 传感器（ADS1115 I2C）采集，单位 μS/cm
"""
import sqlite3
import time
import logging
from config import (
    DB_PATH,
    AIR_SENSOR_PORT,
    AIR_SENSOR_BAUD,
    TDS_COMPENSATION_TEMPERATURE_C,
)

# sensor_reader 是 brain/ 目录下的核心驱动模块，直接导入
from sensor_reader import HoujiSensor
from tds_reader import read_tds

log = logging.getLogger("houji.sensor")

# 全局环境传感器实例
_air_sensor = None

def init_db():
    """初始化数据库，若表不存在则创建（不破坏已有数据）"""
    with sqlite3.connect(DB_PATH) as conn:
        # WAL 模式：减少写操作对 SD 卡的冲德，降低磨损
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL    NOT NULL,
                temp      REAL,
                humidity  REAL,
                co2       REAL,
                ch2o      REAL,
                tvoc      REAL,
                pm25      REAL,
                pm10      REAL,
                ec        REAL,
                ph        REAL
            )
        """)
        conn.commit()


def log_reading(temp=None, humidity=None, co2=None, ch2o=None, tvoc=None, pm25=None, pm10=None, ec=None, ph=None):
    """写入一条传感器读数"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO sensor_readings 
               (timestamp, temp, humidity, co2, ch2o, tvoc, pm25, pm10, ec, ph) 
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (time.time(), temp, humidity, co2, ch2o, tvoc, pm25, pm10, ec, ph)
        )
        conn.commit()


def get_latest(n=10) -> list[dict]:
    """查询最近 n 条传感器数据"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT ?", (n,)
        ).fetchall()
    return [dict(r) for r in rows]


def _valid_range(name, value, minimum, maximum):
    """将协议合法但物理上明显无效的瞬时值转为缺失值。"""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        log.warning(f"[传感器] {name} 非数值，已忽略: {value!r}")
        return None
    if minimum <= numeric <= maximum:
        return value
    log.warning(
        f"[传感器] {name} 超出可信范围 {minimum}~{maximum}，已忽略: {value!r}"
    )
    return None


def read_sensors() -> dict:
    """独立读取空气与 EC；任一传感器失败不遮蔽另一传感器结果。"""
    global _air_sensor

    data = {
        "temp": None, "humidity": None, "co2": None,
        "ch2o": None, "tvoc": None, "pm25": None, "pm10": None,
        "ec": None,
        "ph": None,
    }

    # ---- 1. UART 环境传感器 ----
    try:
        if _air_sensor is None:
            _air_sensor = HoujiSensor(port=AIR_SENSOR_PORT, baudrate=AIR_SENSOR_BAUD)
            _air_sensor.connect()

        air_read_ok = False
        for attempt in range(3):
            frame = _air_sensor.read_frame()
            if not frame:
                log.warning(f"[传感器] 第 {attempt + 1} 次未获取帧，重试中...")
                time.sleep(1)
                continue
            result = _air_sensor.parse_data(frame)
            if not result:
                continue

            temperature = _valid_range("温度", result.get("Temp"), -40.0, 85.0)
            humidity = _valid_range("湿度", result.get("Humi"), 0.1, 100.0)
            if temperature is None or humidity is None:
                continue

            data.update({
                "temp": temperature,
                "humidity": humidity,
                "co2": _valid_range("CO2", result.get("CO2"), 250, 10000),
                "ch2o": _valid_range("CH2O", result.get("CH2O"), 0, 10000),
                "tvoc": _valid_range("TVOC", result.get("TVOC"), 0, 60000),
                "pm25": _valid_range("PM2.5", result.get("PM2.5"), 0, 5000),
                "pm10": _valid_range("PM10", result.get("PM10"), 0, 5000),
            })
            air_read_ok = True
            break

        if not air_read_ok:
            raise TimeoutError("连续 3 次未获得有效 UART 环境帧")
    except Exception as exc:
        log.error(f"[环境传感器] 读取失败: {exc}")
        try:
            if _air_sensor and _air_sensor.ser and _air_sensor.ser.is_open:
                _air_sensor.ser.close()
        except Exception:
            pass
        _air_sensor = None

    # ---- 2. EC/TDS ----
    try:
        data["ec"] = read_tds(temperature=TDS_COMPENSATION_TEMPERATURE_C)
    except Exception as exc:
        log.error(f"[EC传感器] 读取失败: {exc}")
        data["ec"] = None

    return data
