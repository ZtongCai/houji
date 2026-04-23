import time
import cv2
from pathlib import Path

# 动态测试路径
output_jpg = Path(__file__).resolve().parent / "test_snapshot.jpg"

print("--- [后稷项目] USB 摄像头模块测试 ---")
print("正连接到摄像头...")

try:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 无法打开 USB 摄像头")
        exit(1)
        
    print("\n等待传感器曝光调整...")
    for _ in range(10):
        cap.read()
        time.sleep(0.1)
        
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        # 旋转180度
        frame = cv2.flip(frame, -1)
        cv2.imwrite(str(output_jpg), frame)
        size_kb = output_jpg.stat().st_size / 1024
        print(f"\n✅ 拍摄成功！咔嚓！")
        print(f"✅ 图片落盘路径: {output_jpg}")
        print(f"✅ 文件大小: {size_kb:.1f} KB")
    else:
        print("\n❌ 拍摄失败：无法捕捉画面。")

except Exception as e:
    print(f"\n❌ 操作摄像头失败，报错如下: {e}")
