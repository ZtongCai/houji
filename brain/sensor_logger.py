"""
传感器数据采集与 SQLite 存储
表结构：
  sensor_readings(id, timestamp, temp, humidity, co2, ch2o, tvoc, pm25, pm10, ec, ph)
"""
import sqlite3
import time
from config import DB_PATH

# sensor_reader 是 brain/ 目录下的核心驱动模块，直接导入
from sensor_reader import HoujiSensor

# 全局环境传感器实例
_air_sensor = None

def init_db():
    """初始化数据库，创建传感器数据表"""
    with sqlite3.connect(DB_PATH) as conn:
        # 开发早期测试阶段：强制删掉旧表解决字段冲突
        conn.execute("DROP TABLE IF EXISTS sensor_readings")
        
        conn.execute("""
            CREATE TABLE sensor_readings (
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
        "temp": None,
        "humidity": None,
        "co2": None,
        "ch2o": None,
        "tvoc": None,
        "pm25": None,
        "pm10": None,
        "ec": None,  # TODO: 待接入 EC 传感器
        "ph": None   # TODO: 待接入 pH 传感器
    }
    
    try:
        # ---- 1. 读取环境 7 合 1 传感器 ----
        if _air_sensor is None:
            _air_sensor = HoujiSensor(port='/dev/ttyAMA0', baudrate=9600)
            _air_sensor.connect()
            
        frame = _air_sensor.read_frame()
        if frame:
            result = _air_sensor.parse_data(frame)
            if result:
                # 过滤说明书中提到的异常帧 (温湿碳全为 0)
                if not (result['Temp'] == 0.0 and result['Humi'] == 0.0 and result['CO2'] == 0):
                    data["temp"] = result.get('Temp')
                    data["humidity"] = result.get('Humi')
                    data["co2"] = result.get('CO2')
                    data["ch2o"] = result.get('CH2O')
                    data["tvoc"] = result.get('TVOC')
                    data["pm25"] = result.get('PM2.5')
                    data["pm10"] = result.get('PM10')
                    
        # ---- 2. 预留：读取水质传感器 (EC/pH) ----
        # 接下来在这里补充 EC 与 PH 的代码...
        
    except Exception as e:
        print(f"Error reading sensors: {e}")
        # 出错时重置串口，方便下次重试
        if _air_sensor and _air_sensor.ser:
            _air_sensor.ser.close()
        _air_sensor = None
        
    return data
