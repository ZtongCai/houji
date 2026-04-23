import cv2
import time
from pathlib import Path

def test_usb_camera():
    print("--- [后稷项目] USB 摄像头通用测试 ---")
    output_jpg = Path(__file__).resolve().parent / "test_usb_snapshot.jpg"
    
    # 0 代表系统识别到的第一个摄像头（通常是 /dev/video0）
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ 错误：无法打开 USB 摄像头，请检查是否插紧，或尝试更改参数为 cv2.VideoCapture(1)等。")
        return

    print("摄像头已连接，等待感光元件曝光调整 (约一秒钟)...")
    for _ in range(10):
        cap.read()  # 抛弃刚启动时的黑屏或偏色帧
        time.sleep(0.1)
        
    ret, frame = cap.read()
    
    if ret:
        # 旋转180度 (上下左右都翻转)，解决倒置问题
        frame = cv2.flip(frame, -1)
        
        cv2.imwrite(str(output_jpg), frame)
        size_kb = output_jpg.stat().st_size / 1024
        print(f"\n✅ 拍摄成功！咔嚓！")
        print(f"✅ 图片落盘路径: {output_jpg}")
        print(f"✅ 文件大小: {size_kb:.1f} KB")
        h, w = frame.shape[:2]
        print(f"✅ 分辨率: {w}x{h}")
    else:
        print("\n❌ 错误：捕捉画面失败。")
        
    cap.release()

if __name__ == "__main__":
    test_usb_camera()
