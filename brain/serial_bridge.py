"""
串口通信桥接（Pi5 ↔ Pico）
指令协议（JSON Lines）：
  发送: {"cmd": "relay", "id": 1, "state": 1}
  接收: {"status": "ok", "id": 1}
"""
import json
import logging
import threading
import serial
from config import SERIAL_PORT, SERIAL_BAUD

log = logging.getLogger("houji.serial")


class SerialBridge:
    def __init__(self):
        self.ser = None
        self._lock = threading.Lock()  # 防止多线程并发写串口
        self.connect()

    def connect(self):
        """建立串口连接，失败时记录警告，不 exit"""
        try:
            self.ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=2)
            log.info(f"[串口] 已连接 Pico ({SERIAL_PORT})")
        except Exception as e:
            log.warning(f"[串口] 连接失败，继电器暂时不可用: {e}")
            self.ser = None

    def send_command(self, cmd: dict) -> dict | None:
        """发送 JSON 指令，返回 Pico 回执；加锁防止多线程竞争，失败时重连一次"""
        with self._lock:
            if not self.ser:
                self.connect()
            if not self.ser:
                return None
            try:
                self.ser.write((json.dumps(cmd) + "\n").encode())
                raw = self.ser.readline().decode().strip()
                return json.loads(raw) if raw else None
            except Exception as e:
                log.warning(f"[串口] 发送失败，尝试重连: {e}")
                self.connect()
                return None

    def close(self):
        if self.ser:
            self.ser.close()
