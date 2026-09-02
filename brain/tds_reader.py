"""
TDS 营养液浓度传感器驱动
硬件：TDS 探头 → ADS1115 ADC (I2C, 默认地址 0x48) → Pi 5
读取 A0 通道电压，经温度补偿后用三次多项式换算为 TDS 浓度 (ppm)，
再换算为 EC (μS/cm)返回。单位与 config.py / sensor_logger 一致。

温度补偿原理：电导率随温度升高约每 1°C 增 2%，
补偿公式：compensated_V = raw_V / (1 + 0.02 * (T - 25))
将补偿后电压代入多项式，等效为折算到 25°C 基准下的 TDS。
"""
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# 全局 I2C/ADC 实例，避免重复初始化
_ads = None

def _get_ads():
    global _ads
    if _ads is None:
        i2c = busio.I2C(board.SCL, board.SDA)
        _ads = ADS.ADS1115(i2c)
    return _ads

def read_tds(temperature: float = 25.0) -> float | None:
    """读取营养液 EC 浓度（μS/cm），失败时返回 None

    :param temperature: 当前液体/环境温度（°C），用于温度补偿，默认 25°C
    """
    ads = _get_ads()
    chan = AnalogIn(ads, 0)  # A0 通道
    voltage = chan.voltage

    # 温度补偿：将原始电压折算回 25°C 基准
    compensation = 1.0 + 0.02 * (temperature - 25.0)
    compensated_v = voltage / compensation

    if compensated_v < 0.1:
        # 低于探头有效电压时视为“无有效读数”，不能把断线误作 EC=0。
        return None

    # 该多项式的原始输出单位即为 μS/cm（DFRobot 官方公式，基准 25°C）
    # 注意：有些资料写的是先算 ppm 再 ×2，本质相同，此处省略中间步骤直接输出 EC
    ec_us = 133.42 * compensated_v**3 - 255.86 * compensated_v**2 + 857.39 * compensated_v
    return round(ec_us, 1)
