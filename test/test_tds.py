import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

from tds_reader import read_tds

def run_test():
    print("--- [后稷项目] TDS 水质传感器 (ADS1115) 测试 ---")
    print("正在连接 I2C 设备 (默认地址 0x48)...")
    print("按 Ctrl+C 终止测试\n")
    try:
        while True:
            ec = read_tds()
            print(f"EC: {ec:.1f} μS/cm" if ec is not None else "无有效 EC 读数")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✅ 测试由用户主动终止。")
    except Exception as e:
        print(f"\n❌ 通信发生异常: {e}")
        print("请检查 I2C 接线 (SDA/SCL) 或是否正确使能了树莓派的 I2C 接口。")

if __name__ == "__main__":
    run_test()
