"""
传感器数据采集与 SQLite 存储
表结构：
  sensor_readings(id, timestamp, temp, humidity, co2, ch2o, tvoc, pm25, pm10, ec, ph)
  ec 字段由 TDS 传感器（ADS1115 I2C）采集，单位 μS/cm
"""
import sqlite3
import time
import logging
from config import DB_PATH

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


def read_sensors() -> dict:
    """从硬件读取传感器数值，整合环境与水质数据"""
    global _air_sensor

    data = {
        "temp": None, "humidity": None, "co2": None,
        "ch2o": None, "tvoc": None, "pm25": None, "pm10": None,
        "ec": None,   # TDS 传感器读数 (μS/cm)，ADS1115 I2C
        "ph": None    # TODO: 待接入 pH 传感器
    }

    try:
        # ---- 1. 读取环境 7 合 1 传感器（最多重试 3 次）----
        if _air_sensor is None:
            _air_sensor = HoujiSensor(port='/dev/ttyAMA0', baudrate=9600)
            _air_sensor.connect()

        for attempt in range(3):
            frame = _air_sensor.read_frame()
            if not frame:
                log.warning(f"[传感器] 第 {attempt+1} 次未获取帧，重试中...")
                time.sleep(1)
                continue
            result = _air_sensor.parse_data(frame)
            if not result:
                continue
            # 过滤说明书中提到的异常帧 (温湿碳全为 0)
            if result['Temp'] == 0.0 and result['Humi'] == 0.0 and result['CO2'] == 0:
                continue
            data["temp"]     = result.get('Temp')
            data["humidity"] = result.get('Humi')
            data["co2"]      = result.get('CO2')
            data["ch2o"]     = result.get('CH2O')
            data["tvoc"]     = result.get('TVOC')
            data["pm25"]     = result.get('PM2.5')
            data["pm10"]     = result.get('PM10')
            break  # 成功就退出重试

        # ---- 2. 读取 TDS 营养液传感器（ADS1115 I2C），ec 字段存 μS/cm ----
        # 传入7合1实测温度做补偿，获取不到则默认 25°C
        temp_for_tds = data["temp"] if data["temp"] is not None else 25.0
        data["ec"] = read_tds(temperature=temp_for_tds)

        # ---- 3. 预留：读取 pH 传感器 ----

    except Exception as e:
        log.error(f"[传感器] 读取失败: {e}")
        if _air_sensor:
            if _air_sensor.ser and _air_sensor.ser.is_open:
                _air_sensor.ser.close()
            _air_sensor = None

    return data
