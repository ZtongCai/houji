# MicroPython 继电器驱动（运行在树莓派 Pico）
# 继电器编号约定：1=补光灯 2=排气扇 3=蠕动泵
from machine import Pin

# 继电器编号 → GPIO 引脚映射（根据实际接线修改）
RELAY_PIN_MAP = {
    1: 2,   # 补光灯 → GP2
    2: 3,   # 排气扇  → GP3
    3: 4,   # 蠕动泵  → GP4
}


class RelayDriver:
    def __init__(self):
        # 初始化所有继电器引脚为输出，默认关闭（高电平=断开，低电平=闭合）
        self.pins = {
            rid: Pin(gpio, Pin.OUT, value=1)
            for rid, gpio in RELAY_PIN_MAP.items()
        }

    def set(self, relay_id: int, state: int):
        """
        控制指定继电器
        :param relay_id: 继电器编号 (1/2/3)
        :param state:    1=开启 0=关闭
        """
        pin = self.pins.get(relay_id)
        if pin is None:
            return
        # 低电平触发继电器：state=1 → pin=0
        pin.value(0 if state else 1)

    def all_off(self):
        """紧急关闭所有继电器"""
        for pin in self.pins.values():
            pin.value(1)
