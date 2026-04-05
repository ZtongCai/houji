import time
from pathlib import Path
from picamera2 import Picamera2

# 动态测试路径
output_jpg = Path(__file__).resolve().parent / "test_snapshot.jpg"

print("--- [后稷项目] Picamera2 图像传感器测试 ---")
print("正连接到摄像头...")

try:
    cam = Picamera2()
    
    print("\n等待传感器预热并测光...")
    # 可选配置，先配置为最高分辨率
    # cam.configure(cam.create_still_configuration(main={"size": (1920, 1080)}))
    cam.start()
    time.sleep(1) # 热身一秒防黑屏
    
    cam.capture_file(str(output_jpg))
    cam.close()
    
    if output_jpg.exists():
        size_kb = output_jpg.stat().st_size / 1024
        print(f"\n✅ 拍摄成功！咔嚓！")
        print(f"✅ 图片落盘路径: {output_jpg}")
        print(f"✅ 文件大小: {size_kb:.1f} KB")
    else:
        print("\n❌ 拍摄失败：尽管未报错但没找到生成的文件。")

except Exception as e:
    print(f"\n❌ 操作摄像头失败，报错如下: {e}")
