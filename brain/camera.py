"""
摄像头快照模块
使用 opencv-python 库从 USB 摄像头定时拍照并保存至 data/snapshots/
"""
import time
from datetime import datetime
import cv2
from pathlib import Path
from config import SNAPSHOT_DIR, CAMERA_INDEX

def take_snapshot() -> Path | None:
    """拍摄一张快照，文件名为精确定时，返回文件路径"""
    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = SNAPSHOT_DIR / f"{time_str}.jpg"

    cap = cv2.VideoCapture(CAMERA_INDEX)
    try:
        if not cap.isOpened():
            print("[摄像头] 无法打开 USB 摄像头")
            return None

        # 预热并跳过初始废帧，等待感光元件的自动曝光(AE)算法适应强光。
        # 摄像头必须在运行态时，自动曝光才会开始调整。单纯的主程序睡眠没用。
        # 这里连吞 50 帧（如果是 30fps，大约需要强行感光运行接近 1.6 秒）
        for _ in range(50):
            cap.read()

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
