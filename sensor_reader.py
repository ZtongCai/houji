import serial
import time

class HoujiSensor:
    def __init__(self, port='/dev/ttyAMA0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"--- [Houji System] Sensor Connected ({self.port}) ---")
            # 清空启动时的旧缓存
            self.ser.reset_input_buffer() 
        except Exception as e:
            print(f"Serial connection failed: {e}")
            exit(1)

    def read_frame(self):
        """精准捕获 17 字节的有效数据帧"""
        if not self.ser: return None
        
        while True:
            if self.ser.in_waiting > 0:
                char1 = self.ser.read(1)
                if char1 == b'\x3c':
                    char2 = self.ser.read(1)
                    if char2 == b'\x02':
                        rest_of_data = self.ser.read(15)
                        if len(rest_of_data) == 15:
                            return b'\x3c\x02' + rest_of_data
            time.sleep(0.01)

    def parse_data(self, data):
        """根据说明书解析协议"""
        # 1. 校验和计算
        checksum = sum(data[0:16]) & 0xFF
        if checksum != data[16]:
            return None

        # 2. 提取各项数据
        eco2 = (data[2] << 8) | data[3]
        ech2o = (data[4] << 8) | data[5]     # 甲醛 (第七个变量)
        tvoc = (data[6] << 8) | data[7]
        pm25 = (data[8] << 8) | data[9]
        pm10 = (data[10] << 8) | data[11]

        # 3. 温度解析
        temp_is_negative = (data[12] & 0x80) != 0
        temp_int = data[12] & 0x7F
        temp_dec = data[13]
        temperature = (temp_int + temp_dec / 10.0)
        if temp_is_negative:
            temperature = -temperature

        # 4. 湿度解析
        humi_int = data[14]
        humi_dec = data[15]
        humidity = humi_int + humi_dec / 10.0

        return {
            "CO2": eco2,
            "CH2O": ech2o,
            "TVOC": tvoc,
            "PM2.5": pm25,
            "PM10": pm10,
            "Temp": round(temperature, 1),
            "Humi": round(humidity, 1)
        }

    def monitor(self):
        self.connect()
        print("Start monitoring environmental data (Press Ctrl+C to exit)...\n")
        try:
            while True:
                frame = self.read_frame()
                if frame:
                    result = self.parse_data(frame)
                    if result:
                        # 【核心防抖过滤】如果温度、湿度和 CO2 同时为 0，视为传感器内部校准异常，丢弃该帧
                        if result['Temp'] == 0.0 and result['Humi'] == 0.0 and result['CO2'] == 0:
                            continue
                            
                        print(f"[{time.strftime('%H:%M:%S')}] Data Update:")
                        print(f" Temp: {result['Temp']} C    | Humi: {result['Humi']} %")
                        print(f" PM2.5: {result['PM2.5']:3d}    | PM10: {result['PM10']:3d}")
                        print(f" CO2: {result['CO2']:5d}  | TVOC: {result['TVOC']:3d}  | CH2O: {result['CH2O']:3d}")
                        print("-" * 50)
                time.sleep(0.5) 
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()

if __name__ == "__main__":
    sensor = HoujiSensor(port='/dev/ttyAMA0', baudrate=9600)
    sensor.monitor()