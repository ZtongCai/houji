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
    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super(SerialBridge, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.ser = None
        self._lock = threading.RLock()  # 防止多线程并发写串口
        self.connect()

    def connect(self):
        """建立串口连接，支持端口偏移自适应与死锁自动修复"""
        import glob

        # 1. 释放旧句柄防死锁 (极其重要，否则断电后再次分配的新 ACM1 永远连不上)
        if getattr(self, "ser", None) is not None:
            try:
                self.ser.close()
            except Exception as e:
                log.debug(f"[串口] 清理旧句柄报错: {e}")
        self.ser = None

        # 很多时候继电器闭合瞬间的电磁干扰（EMI）或欠压会导致 Pico 闪断重启
        # 重启后 Linux 经常把它的口分配成 ttyACM1 或 ttyACM2
        discovered = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"), reverse=True)
        ports = [SERIAL_PORT] + [port for port in discovered if port != SERIAL_PORT]

        # 2. 优先稳定的 by-id 配置；设备重枚举路径只作为退路。
        for target_port in ports:
            try:
                # 使用单例长连接，禁止拉低 DTR/RTS，避免引起 Pico 硬件级复位和高阻态继电器吸合
                ser = serial.Serial()
                ser.port = target_port
                ser.baudrate = SERIAL_BAUD
                ser.timeout = 2
                ser.setDTR(False)
                ser.setRTS(False)
                ser.open()
                self.ser = ser
                log.info(f"[串口] 已连接 Pico ({target_port}) [长连接/抗复位/自动寻址模式]")
                return  # 成功连上，立即返回
            except Exception as e:
                log.warning(f"[串口] 连接失败，无法打开口 {target_port} : {e}")

        log.error("[串口] 彻底连接失败，没有任何可用的有效端口！")

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
                resp = json.loads(raw)
                self._validate_response(cmd, resp)
                return resp
            except Exception as e:
                log.warning(f"[串口] 发送失败，尝试重连并重试: {e}")
                self.connect()
                if self.ser:
                    try:
                        self.ser.write((json.dumps(cmd) + "\n").encode())
                        raw = self.ser.readline().decode().strip()
                        if not raw:
                            raise Exception("重连后串口仍超时，目标未响应。")
                        resp = json.loads(raw)
                        self._validate_response(cmd, resp)
                        return resp
                    except Exception as e2:
                        log.error(f"[串口] 重连后重新发送仍然失败: {e2}")
                return None

    @staticmethod
    def _validate_response(cmd: dict, resp: dict):
        if not isinstance(resp, dict) or resp.get("status") != "ok":
            raise ValueError(f"Pico 返回失败: {resp!r}")
        if cmd.get("cmd") == "relay" and resp.get("id") != cmd.get("id"):
            raise ValueError(f"Pico 回执继电器不匹配: cmd={cmd!r}, resp={resp!r}")

    def query_status(self) -> dict | None:
        """获取 Pico 当前继电器引脚的真实电平状态，闭环监控"""
        resp = self.send_command({"cmd": "status"})
        if resp and resp.get("status") == "ok":
            return resp.get("state")
        return None
