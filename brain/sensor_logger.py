"""
传感器数据采集与 SQLite 存储
表结构：
  sensor_readings(id, timestamp, temp, humidity, ph, ec)
"""
import sqlite3
import time
from config import DB_PATH


def init_db():
    """初始化数据库，创建传感器数据表"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL    NOT NULL,
                temp      REAL,
                humidity  REAL,
                ph        REAL,
                ec        REAL
            )
        """)
        conn.commit()


def log_reading(temp=None, humidity=None, ph=None, ec=None):
    """写入一条传感器读数"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sensor_readings (timestamp, temp, humidity, ph, ec) VALUES (?,?,?,?,?)",
            (time.time(), temp, humidity, ph, ec)
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


# TODO: Phase1 —— 接入实际传感器 I2C/ADC 读取
def read_sensors() -> dict:
    """从硬件读取传感器数值（当前返回占位数据）"""
    return {"temp": None, "humidity": None, "ph": None, "ec": None}
