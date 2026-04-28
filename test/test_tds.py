import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

def get_tds_reading():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    # 绕过常量定义，直接传入 0 表示 A0 通道
    chan = AnalogIn(ads, 0)
    
    voltage = chan.voltage
    # 基于水温 25℃ 时的 TDS 经验估算公式
    if voltage < 0.1:
        ec_value = 0
    else:
        ec_value = (133.42 * voltage**3 - 255.86 * voltage**2 + 857.39 * voltage)
        
    return voltage, ec_value

def run_test():
    print("--- [后稷项目] TDS 水质传感器 (ADS1115) 测试 ---")
    print("正在连接 I2C 设备 (默认地址 0x48)...")
    print("按 Ctrl+C 终止测试\n")
    try:
        while True:
            voltage, ec = get_tds_reading()
            print(f"探头实时读取 -> 电压: {voltage:.3f} V | EC 值: {ec:.1f} μS/cm")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✅ 测试由用户主动终止。")
    except Exception as e:
        print(f"\n❌ 通信发生异常: {e}")
        print("请检查 I2C 接线 (SDA/SCL) 或是否正确使能了树莓派的 I2C 接口。")

if __name__ == "__main__":
    run_test()
