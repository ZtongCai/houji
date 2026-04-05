import sys
import time
from pathlib import Path

# 将模块路径加进环境变量，以确保能引到我们的文件
sys.path.append(str(Path(__file__).resolve().parent.parent / 'brain'))

from sensor_logger import init_db, read_sensors, log_reading, get_latest

print("--- [后稷项目] 测试传感器入库流水线 ---")

print("1. 正在初始化 SQLite 数据库...")
init_db()
print("   ✅ 数据库表格初始化成功！")

print("2. 正在尝试从 7合1 传感器抓取数据帧 (等待中...)")
try:
    data = read_sensors()
    if data and any(v is not None for v in data.values()):
        print(f"   ✅ 成功抓取传感器数据：{data}")
        
        print("3. 正在将该条数据写入 SQLite...")
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
        print("   ✅ 写入完毕！")
    else:
        print("   ❌ 没有抓到有效数据帧，或全部为None (请确认串口传感器接线正常)")

    print("\n--- 数据库最新存储验证 ---")
    rows = get_latest(5)
    for i, row in enumerate(rows):
        print(f"最近第 {i+1} 条: 时间戳={row['timestamp']:.1f}, 温度={row['temp']}°C, 湿度={row['humidity']}%, CO2={row['co2']}ppm")

except Exception as e:
    print(f"❌ 测试过程中发生错误: {e}")
