"""
后稷主控入口 (Pi 5)
负责协调传感器采集、AI 决策、摄像头快照的主循环
"""
import time
import logging
from config import (
    SENSOR_INTERVAL, SNAPSHOT_INTERVAL, AI_DECISION_INTERVAL, DATA_DIR
)

# 配置日志：同时输出到控制台和独立的运行日志（不污染 AI thought.log）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DATA_DIR / "houji.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("houji")


from sensor_logger import init_db, read_sensors, log_reading
from camera import take_snapshot
from ai_engine import run_cycle

def main():
    log.info("🌱 后稷启动 —— 水培生菜 AI 守护者上线")
    
    # 启动前初始化数据库表结构
    init_db()

    last_sensor   = 0
    last_snapshot = 0
    last_ai       = 0

    while True:
        now = time.time()

        # 传感器采集（每分钟一次）
        if now - last_sensor >= SENSOR_INTERVAL:
            log.info("[传感器] 正在采集环境数据...")
            try:
                data = read_sensors()
                log_reading(
                    temp=data.get("temp"),
                    humidity=data.get("humidity"),
                    co2=data.get("co2"),
                    ch2o=data.get("ch2o"),
                    tvoc=data.get("tvoc"),
                    pm25=data.get("pm25"),
                    pm10=data.get("pm10"),
                    ec=data.get("ec"),
                    ph=data.get("ph")
                )
                log.info(f"[传感器] 入库成功: {data}")
            except Exception as e:
                log.error(f"[传感器] 采集异常: {e}")
            last_sensor = now

        # 摄像头快照
        if now - last_snapshot >= SNAPSHOT_INTERVAL:
            log.info("[摄像头] 定时快照拍摄中...")
            try:
                # ── 夜间「闪光灯」逻辑 ──
                from datetime import datetime
                from config import LIGHT_ON_HOUR, LIGHT_OFF_HOUR
                from serial_bridge import SerialBridge
                
                hour = datetime.now().hour
                is_night = (hour >= LIGHT_OFF_HOUR or hour < LIGHT_ON_HOUR)
                bridge = None
                
                if is_night:
                    log.info("[摄像头] 夜间全黑环境，开启补光灯充当闪光灯 (3秒预热)...")
                    bridge = SerialBridge()
                    bridge.send_command({"cmd": "relay", "id": 8, "state": 1})
                    time.sleep(3) # 让摄像头的自动曝光和白平衡有时间适应强光

                # 拍摄照片
                snap_path = take_snapshot()
                if snap_path:
                    log.info(f"[摄像头] 快照入库: {snap_path}")

                # 拍完立马关灯
                if is_night and bridge:
                    log.info("[摄像头] 拍摄完成，恢复夜间熄灯静息状态。")
                    bridge.send_command({"cmd": "relay", "id": 8, "state": 0})
                    bridge.close()

            except Exception as e:
                log.error(f"[摄像头] 拍摄或补光异常: {e}")
            last_snapshot = now

        # AI 大模型决策（每 5 分钟一次，与快照同步）
        if now - last_ai >= AI_DECISION_INTERVAL:
            log.info("[AI] 触发 LangGraph 决策周期...")
            try:
                run_cycle()
            except Exception as e:
                log.error(f"[AI] 决策异常: {e}")
            last_ai = now

        time.sleep(5)


if __name__ == "__main__":
    main()

