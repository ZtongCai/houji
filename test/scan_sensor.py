import serial
import time

# 锁定频道
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)

print("--- [后稷项目] 环境传感器监听中... ---")
print("提示：如果屏幕一直没动静，请尝试把传感器的 TX 换到 Pin 8 试试（万一厂家标反了）。")

try:
    while True:
        if ser.in_waiting > 0:
            # 读取一行原始数据
            raw_data = ser.readline()
            
            # 尝试解码为文本
            try:
                text_data = raw_data.decode('utf-8').strip()
                print(f"[{time.strftime('%H:%M:%S')}] 文本数据: {text_data}")
            except:
                # 如果是十六进制数据（Modbus），则显示 Hex
                print(f"[{time.strftime('%H:%M:%S')}] 十六进制: {raw_data.hex()}")
        
        time.sleep(0.1) # 降低 CPU 占用
except KeyboardInterrupt:
    print("\n用户停止监听。")
    ser.close()
