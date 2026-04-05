# MicroPython 主循环（运行在树莓派 Pico）
# 持续监听串口，解析 JSON 指令，驱动继电器
import ujson
import sys
from relay_driver import RelayDriver

relay = RelayDriver()

while True:
    # 从 Pi 5 读取一行 JSON 指令
    line = sys.stdin.readline().strip()
    if not line:
        continue

    cmd = ujson.loads(line)

    if cmd.get("cmd") == "relay":
        relay_id = cmd.get("id", 0)
        state    = cmd.get("state", 0)
        relay.set(relay_id, state)
        # 回执确认
        sys.stdout.write(ujson.dumps({"status": "ok", "id": relay_id}) + "\n")
