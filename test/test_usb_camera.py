import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

from camera import take_snapshot

def test_usb_camera():
    print("--- [后稷项目] USB 摄像头通用测试 ---")
    snapshot = take_snapshot()
    if snapshot is None:
        raise SystemExit("❌ 摄像头拍摄失败")
    print(f"✅ 图片落盘路径: {snapshot}")
    print(f"✅ 文件大小: {snapshot.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    test_usb_camera()
