"""
串口通信桥接（Pi5 ↔ Pico）
负责向 Pico 发送继电器控制指令，并接收确认回执
指令协议（JSON Lines）：
  发送: {"cmd": "relay", "id": 1, "state": 1}
  接收: {"status": "ok", "id": 1}
"""
import json
import serial
from config import SERIAL_PORT, SERIAL_BAUD


class SerialBridge:
    def __init__(self):
        # TODO: Phase1 —— 初始化串口连接
        self.ser = None

    def connect(self):
        self.ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=2)

    def send_command(self, cmd: dict) -> dict | None:
        """发送 JSON 指令，返回 Pico 回执"""
        if not self.ser:
            return None
        self.ser.write((json.dumps(cmd) + "\n").encode())
        raw = self.ser.readline().decode().strip()
        return json.loads(raw) if raw else None

    def close(self):
        if self.ser:
            self.ser.close()
