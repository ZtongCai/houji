# MicroPython 主循环（运行在树莓派 Pico）
# 持续监听串口，解析 JSON 指令，驱动继电器
import ujson
import sys
from relay_driver import RelayDriver

import select

relay = RelayDriver()

# 注册标准输入到轮询器，避免串口读取时阻塞死机
poll_obj = select.poll()
poll_obj.register(sys.stdin, select.POLLIN)

while True:
    # 每次轮询等 10ms，没有指令输入就立刻跳过，不妨碍执行后续的延时或其他异步任务
    if poll_obj.poll(10):
        # 从 Pi 5 读取一行 JSON 指令
        line = sys.stdin.readline().strip()
        if not line:
            continue

        try:
            cmd = ujson.loads(line)

            if cmd.get("cmd") == "relay":
                relay_id = cmd.get("id", 0)
                state    = cmd.get("state", 0)
                relay.set(relay_id, state)
                # 回执确认
                sys.stdout.write(ujson.dumps({"status": "ok", "id": relay_id}) + "\n")
        except Exception as e:
            # 忽略解析错误或者打印日志
            sys.stdout.write(ujson.dumps({"status": "error", "msg": str(e)}) + "\n")
