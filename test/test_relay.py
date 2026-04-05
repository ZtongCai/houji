import time
import json
import serial

relay_port = '/dev/ttyACM0'  # 你的 Pico 默认端口大概率是这个
baud_rate = 115200

print(f"--- [后稷项目] 连接 Spine 神经中枢 ({relay_port}) ---")

try:
    ser = serial.Serial(relay_port, baud_rate, timeout=1)
    time.sleep(2) # 给 Pico 一点连接缓冲时间
    
    print("\n准备测试新烧录的 JSON 指令解析器 ...\n")
    
    # 模拟开启第 1 路继电器 (12V蠕动泵位)
    print("下发 [营养液蠕动泵 (Relay 1)] => ON")
    cmd_on = {"cmd": "relay", "id": 1, "state": 1}
    ser.write((json.dumps(cmd_on) + "\n").encode('utf-8'))
    print("⬅️ Pico 回执:", ser.readline().decode('utf-8').strip())
    
    time.sleep(2)  # 给它转 2 秒钟
    
    print("下发 [营养液蠕动泵 (Relay 1)] => OFF")
    cmd_off = {"cmd": "relay", "id": 1, "state": 0}
    ser.write((json.dumps(cmd_off) + "\n").encode('utf-8'))
    print("⬅️ Pico 回执:", ser.readline().decode('utf-8').strip())
    
    print("\n--- ✅ 如果听到清脆的嗒嗒声，说明全链路打通完成！ ---")

except Exception as e:
    print(f"通信失败，请检查连线: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
