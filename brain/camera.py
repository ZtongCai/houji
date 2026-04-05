"""
摄像头快照模块（Pi 5 + Camera V1.3）
使用 picamera2 库，定时拍照并保存至 data/snapshots/
"""
import time
from pathlib import Path
from config import SNAPSHOT_DIR

# TODO: Phase1 —— 在 Pi 5 上取消注释以下导入
from picamera2 import Picamera2

def take_snapshot() -> Path | None:
    """拍摄一张快照，文件名为时间戳，返回文件路径"""
    filename = SNAPSHOT_DIR / f"{int(time.time())}.jpg"

    try:
        cam = Picamera2()
        cam.start_and_capture_file(str(filename))
        cam.close()
        print(f"[摄像头] 快照拍摄完成: {filename}")
        return filename
    except Exception as e:
        print(f"[摄像头] 发生异常: {e}")
        return None
