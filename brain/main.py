"""后稷主控入口：采集、快照、AI 分析与可选的安全控制。"""

import json
import logging
import time
from datetime import datetime

from config import (
    AI_DECISION_INTERVAL,
    AI_ENABLED,
    CAMERA_ENABLED,
    CAMERA_FLASH_ENABLED,
    CONTROL_ENABLED,
    CROP_NAME,
    DATA_DIR,
    GROWTH_STAGE,
    LIGHT_OFF_HOUR,
    LIGHT_ON_HOUR,
    RUN_MODE,
    SENSOR_INTERVAL,
    SNAPSHOT_INTERVAL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DATA_DIR / "houji.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("houji")

from ai_engine import run_cycle
from camera import take_snapshot
from sensor_logger import init_db, log_reading, read_sensors


def _has_meaningful_sensor_data(data: dict) -> bool:
    air_valid = any(data.get(key) is not None for key in ("temp", "humidity", "co2"))
    ec = data.get("ec")
    ec_valid = isinstance(ec, (int, float)) and not isinstance(ec, bool) and ec > 0
    return air_valid or ec_valid


def _write_hardware_status(relays=None, connected=False):
    payload = {
        "timestamp": time.time(),
        "run_mode": RUN_MODE,
        "connected": bool(connected),
        "relays": relays or {},
    }
    with open(DATA_DIR / "hardware_status.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


def _update_hardware_status():
    if not CONTROL_ENABLED:
        _write_hardware_status(connected=False)
        return

    try:
        from serial_bridge import SerialBridge

        status = SerialBridge().query_status()
        _write_hardware_status(relays=status, connected=status is not None)
    except Exception as exc:
        log.error(f"[状态] 获取底层硬件状态失败: {exc}")
        _write_hardware_status(connected=False)


def _capture_snapshot():
    if not CAMERA_ENABLED:
        return

    hour = datetime.now().hour
    is_night = hour >= LIGHT_OFF_HOUR or hour < LIGHT_ON_HOUR
    bridge = None
    flash_on = False
    try:
        if is_night and CONTROL_ENABLED and CAMERA_FLASH_ENABLED:
            from serial_bridge import SerialBridge

            bridge = SerialBridge()
            resp = bridge.send_command({"cmd": "relay", "id": 8, "state": 1})
            flash_on = bool(resp and resp.get("status") == "ok")
            if flash_on:
                time.sleep(3)

        snap_path = take_snapshot()
        if snap_path:
            log.info(f"[摄像头] 快照入库: {snap_path}")
    except Exception as exc:
        log.error(f"[摄像头] 拍摄异常: {exc}")
    finally:
        if flash_on and bridge:
            resp = bridge.send_command({"cmd": "relay", "id": 8, "state": 0})
            if not resp or resp.get("status") != "ok":
                log.error("[安全] 夜间临时补光灯关闭未获得有效回执")


def main():
    log.info(
        "🌱 后稷启动 —— 作物=%s 阶段=%s 模式=%s",
        CROP_NAME,
        GROWTH_STAGE,
        RUN_MODE,
    )
    if not CONTROL_ENABLED:
        if AI_ENABLED:
            log.warning("[安全] observe 模式：AI 仅分析，所有继电器动作均被执行层拦截")
        else:
            log.warning("[安全] observe 模式：AI 与继电器执行均已关闭")

    init_db()
    _write_hardware_status(connected=False)

    last_sensor = 0.0
    last_snapshot = 0.0
    last_ai = 0.0

    while True:
        now = time.time()

        if now - last_sensor >= SENSOR_INTERVAL:
            try:
                data = read_sensors()
                if _has_meaningful_sensor_data(data):
                    log_reading(
                        temp=data.get("temp"),
                        humidity=data.get("humidity"),
                        co2=data.get("co2"),
                        ch2o=data.get("ch2o"),
                        tvoc=data.get("tvoc"),
                        pm25=data.get("pm25"),
                        pm10=data.get("pm10"),
                        ec=data.get("ec"),
                        ph=data.get("ph"),
                    )
                    log.info(f"[传感器] 有效数据已入库: {data}")
                else:
                    log.warning(f"[传感器] 全部读数无效，本轮不入库: {data}")
            except Exception as exc:
                log.error(f"[传感器] 采集异常: {exc}")

            _update_hardware_status()
            last_sensor = now

        if now - last_snapshot >= SNAPSHOT_INTERVAL:
            _capture_snapshot()
            last_snapshot = now

        if AI_ENABLED and now - last_ai >= AI_DECISION_INTERVAL:
            log.info("[AI] 触发分析周期（模式=%s）", RUN_MODE)
            try:
                run_cycle()
            except Exception as exc:
                log.error(f"[AI] 决策异常: {exc}")
            last_ai = now

        time.sleep(2)


if __name__ == "__main__":
    main()
