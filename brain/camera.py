"""
摄像头快照模块
使用 opencv-python 库从 USB 摄像头定时拍照并保存至 data/snapshots/
"""
import time
import cv2
from pathlib import Path
from config import SNAPSHOT_DIR

def take_snapshot() -> Path | None:
    """拍摄一张快照，文件名为时间戳，返回文件路径"""
    filename = SNAPSHOT_DIR / f"{int(time.time())}.jpg"

    cap = cv2.VideoCapture(0)
    try:
        if not cap.isOpened():
            print("[摄像头] 无法打开 USB 摄像头")
            return None

        # 预热并跳过初始暗帧，等待感光元件曝光调整
        for _ in range(10):
            cap.read()
            time.sleep(0.1)

        ret, frame = cap.read()
        if ret:
            # 旋转180度解决硬件倒置问题
            frame = cv2.flip(frame, -1)
            cv2.imwrite(str(filename), frame)
            print(f"[摄像头] 快照拍摄完成: {filename}")
            return filename
        print("[摄像头] 捕捉画面失败")
        return None

    except Exception as e:
        print(f"[摄像头] 发生异常: {e}")
        return None
    finally:
        cap.release()  # 无论成功与否都确保释放摄像头
