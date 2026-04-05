"""
后稷主控入口 (Pi 5)
负责协调传感器采集、AI 决策、摄像头快照的主循环
"""
import time
import logging
from config import (
    SENSOR_INTERVAL, SNAPSHOT_INTERVAL, AI_DECISION_INTERVAL, THOUGHT_LOG_PATH
)

# 配置日志：同时输出到控制台和 thought.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(THOUGHT_LOG_PATH, encoding="utf-8"),
    ],
)
log = logging.getLogger("houji")


def main():
    log.info("🌱 后稷启动 —— 水培生菜 AI 守护者上线")

    last_sensor   = 0
    last_snapshot = 0
    last_ai       = 0

    while True:
        now = time.time()

        # TODO: Phase1 —— 传感器采集
        if now - last_sensor >= SENSOR_INTERVAL:
            log.info("[传感器] 采集中... (TODO)")
            last_sensor = now

        # TODO: Phase1 —— 摄像头快照
        if now - last_snapshot >= SNAPSHOT_INTERVAL:
            log.info("[摄像头] 拍照中... (TODO)")
            last_snapshot = now

        # TODO: Phase2 —— AI 决策
        if now - last_ai >= AI_DECISION_INTERVAL:
            log.info("[AI] 决策中... (TODO)")
            last_ai = now

        time.sleep(5)


if __name__ == "__main__":
    main()
