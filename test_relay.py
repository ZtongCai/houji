import serial
import time

# 锁定 Pico 2 的端口，大概率是 ttyACM0
relay_port = '/dev/ttyACM0' 
baud_rate = 115200 # MicroPython 默认波特率通常是 115200

print(f"--- [后稷项目] 准备唤醒肌肉神经 ({relay_port}) ---")

try:
    ser = serial.Serial(relay_port, baud_rate, timeout=1)
    time.sleep(2) # 刚连上给它一点反应时间

    print("发送吸合指令: RELAY_1_ON")
    ser.write(b"RELAY_1_ON\n")
    
    time.sleep(3) # 保持吸合 3 秒钟（如果你接了设备，现在就已经通电了）
    
    print("发送断开指令: RELAY_1_OFF")
    ser.write(b"RELAY_1_OFF\n")

except Exception as e:
    print(f"通信失败: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("--- 执行完毕 ---")