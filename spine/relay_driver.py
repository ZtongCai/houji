# MicroPython 继电器驱动（运行在树莓派 Pico）
from machine import Pin

# 微雪 (Waveshare) Pico-Relay-B 8路继电器针脚映射
# 针脚定义: 第1路=GP21, 第2路=GP20, ... 第8路=GP14
# 12V 和 220V 仍按照物理隔离的规则分配
RELAY_PIN_MAP = {
    1: 21,  # 12V: 营养液蠕动泵
    2: 20,  # 12V: 进气风扇
    3: 19,  # 12V: 出气风扇
    4: 18,  # 空置/备用隔离带
    5: 17,  # 空置/备用隔离带
    6: 16,  # 空置/备用隔离带
    7: 15,  # 220V: 打氧泵
    8: 14,  # 220V: 补光灯
}

# 微雪 Pico-Relay-B 实际是【低电平触发】：写 0 = 吸合（接通），写 1 = 断开（安全状态）
ACTIVE_LOW = True

class RelayDriver:
    def __init__(self):
        # 初始化所有继电器引脚为输出
        # 断开时的默认状态
        default_val = 1 if ACTIVE_LOW else 0
        self.pins = {
            rid: Pin(gpio, Pin.OUT, value=default_val)
            for rid, gpio in RELAY_PIN_MAP.items()
        }

    def set(self, relay_id: int, state: int):
        """
        控制指定继电器
        :param relay_id: 继电器编号 (1-8)
        :param state:    1=要求开启 0=要求关闭
        """
        pin = self.pins.get(relay_id)
        if pin is None:
            return
            
        if ACTIVE_LOW:
            # 低电平触发：写0开，写1关
            pin.value(0 if state else 1)
        else:
            # 高电平触发：写1开，写0关
            pin.value(1 if state else 0)

    def all_off(self):
        """紧急关闭所有继电器"""
        off_val = 1 if ACTIVE_LOW else 0
        for pin in self.pins.values():
            pin.value(off_val)

    def get_all_status(self):
        """获取所有继电器的当前真实逻辑状态 (1=ON, 0=OFF)"""
        status = {}
        for rid, pin in self.pins.items():
            val = pin.value()
            if ACTIVE_LOW:
                # 低电平触发：硬件为0表示开启(1)，硬件为1表示关闭(0)
                status[str(rid)] = 1 if val == 0 else 0
            else:
                status[str(rid)] = 1 if val == 1 else 0
        return status
