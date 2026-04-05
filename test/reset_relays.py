"""
继电器全部断开复位脚本
用于紧急复位或者程序启动前的安全初始化
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'brain'))

from serial_bridge import SerialBridge

# 所有在用的继电器 ID（1-8 全覆盖）
ALL_RELAYS = [1, 2, 3, 4, 5, 6, 7, 8]

print("--- [后稷项目] 继电器全部断开复位 ---")
bridge = SerialBridge()

if not bridge.ser:
    print("❌ 串口连接失败，请检查 Pico 是否已连接")
    sys.exit(1)

time.sleep(0.5)  # 等待 Pico 初始化

for relay_id in ALL_RELAYS:
    cmd = {"cmd": "relay", "id": relay_id, "state": 0}
    resp = bridge.send_command(cmd)
    print(f"  继电器 {relay_id} => OFF  |  Pico 回执: {resp}")
    time.sleep(0.1)  # 防止发送过快

bridge.close()
print("\n✅ 全部继电器已复位断开！")
