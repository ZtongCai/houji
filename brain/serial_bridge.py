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
        self._lock = threading.RLock()  # 防止多线程并发写串口
        self.connect()

    def connect(self):
        """建立串口连接，支持端口偏移自适应"""
        import glob
        # 很多时候继电器闭合瞬间的电磁干扰（EMI）会导致 Pico 闪断重启
        # 重启后 Linux 经常把它的口分配成 ttyACM1 或 ttyACM2，导致写死的代码找不着
        ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
        target_port = ports[0] if ports else SERIAL_PORT

        try:
            self.ser = serial.Serial(target_port, SERIAL_BAUD, timeout=2)
            log.info(f"[串口] 已连接 Pico ({target_port})")
        except Exception as e:
            log.warning(f"[串口] 连接失败，无法打开口 {target_port} : {e}")
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
                if not raw:
                    raise Exception("串口读取超时或 Pico 已假死 (返回值为空)")
                return json.loads(raw)
            except Exception as e:
                log.warning(f"[串口] 发送失败，尝试重连并重试: {e}")
                self.connect()
                if self.ser:
                    try:
                        self.ser.write((json.dumps(cmd) + "\n").encode())
                        raw = self.ser.readline().decode().strip()
                        if not raw:
                            raise Exception("重连后串口仍超时，目标未响应。")
                        return json.loads(raw)
                    except Exception as e2:
                        log.error(f"[串口] 重连后重新发送仍然失败: {e2}")
                return None

    def close(self):
        if self.ser:
            self.ser.close()
