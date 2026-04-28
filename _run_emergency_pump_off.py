import sys
from pathlib import Path

# 添加 brain 到路径以使用具有容灾抗干扰机制的 SerialBridge
sys.path.append(str(Path(__file__).parent / "brain"))

try:
    from serial_bridge import SerialBridge
    print("🚨 正在调用抗干扰底层协议，紧急关停蠕动泵...")
    bridge = SerialBridge()
    resp = bridge.send_command({"cmd": "relay", "id": 1, "state": 0})
    print(f"✅ 强行关停结果: {resp}")
    bridge.close()
except Exception as e:
    print(f"❌ 紧急救机失败: {e}")
