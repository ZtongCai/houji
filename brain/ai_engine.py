"""
LangGraph AI 决策中枢
架构：sense_node → decide_node → execute_node → log_node
对外暴露 run_cycle() 供 main.py 调用
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TypedDict

# 如果开发环境使用了自签 CA 证书的代理，请设置证书路径：
# os.environ["REQUESTS_CA_BUNDLE"] = "/path/to/proxy-ca.crt"
# 不要全局关闭 SSL 校验！那会让 API Key 暗文暴露在中间人攻击页下。

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from config import (
    GEMINI_API_KEY, GEMINI_FLASH_MODEL,
    THOUGHT_LOG_PATH, SNAPSHOT_DIR,
    LIGHT_ON_HOUR, LIGHT_OFF_HOUR,
)
from sensor_logger import read_sensors, get_latest
from serial_bridge import SerialBridge

log = logging.getLogger("houji.ai")

# 全局串口桥接，避免每次 cycle 重复创建
_bridge: SerialBridge | None = None

# ── Pydantic 结构化输出定义 ──────────────────────────────
class RelayAction(BaseModel):
    relay_id: int            # 继电器编号 1-8
    state: int               # 1=开, 0=关
    duration_seconds: int = 0  # >0 表示定时：开启后自动关闭；0 表示持续到下次决策

class HoujiDecision(BaseModel):
    thought: str                 # AI 推理过程
    actions: list[RelayAction]   # 要执行的继电器动作列表

# ── 全局 LLM 实例（模块加载一次，避免每次决策重建 HTTP client）────────
_llm = ChatGoogleGenerativeAI(
    model=GEMINI_FLASH_MODEL,
    google_api_key=GEMINI_API_KEY,
    temperature=0.3,
).with_structured_output(HoujiDecision)

# ── 系统提示词 ───────────────────────────────────────────
SYSTEM_PROMPT = """你是"后稷"，一个专业的水培生菜 AI 农场主。
你正在守护一个 50x50x100cm 密闭帐篷中的两株水培生菜。

你的可控设备（通过继电器 relay_id 控制）：
- relay_id=1 : 营养液蠕动泵 (12V) - 给根部泵送养液
- relay_id=2 : 进气风扇 (12V) - 吸入新鲜空气
- relay_id=3 : 出气风扇 (12V) - 排出废气
- relay_id=7 : 打氧泵 (220V) - 给营养液增氧
- relay_id=8 : 补光灯 (220V) - 全光谱生长光

【重要】动作字段说明：
- state=1/0 表示开/关
- duration_seconds：
  - 蠕动泵（relay_id=1）：必须设 duration_seconds，范围 5~30s，系统自动定时关闭
  - 打氧泵（relay_id=7）：必须设 duration_seconds，范围 10~120s，系统自动定时关闭
  - 风扇（relay_id=2,3）：通风场景设 duration_seconds（如 60~300s），持续通风设 0
  - 补光灯（relay_id=8）：设 duration_seconds=0，持续开启到下次决策

生长参数参考：
- 温度：18~28°C
- 湿度：60%+
- CO2：800~1200ppm 最佳（过高需通风）
- EC：1000~2000 μS/cm（传感器 ec 字段单位，生长期参考值）
- pH：5.5~6.5（待接入）

请根据当前传感器数据与摄像头图像，给出你的分析判断，并给出需要执行的动作列表。
只列出需要变化的状态，不需要变化的设备不必提及。"""

# ── LangGraph State ──────────────────────────────────────
class HoujiState(TypedDict):
    sensor_data: dict
    history: list[dict]    # 最近N条历史传感器数据，用于趋势判断
    image_path: str | None
    thought: str
    actions: list[dict]
    results: list[dict]


# ── 节点函数 ─────────────────────────────────────────────

def sense_node(state: HoujiState) -> HoujiState:
    """读取最新传感器数据、历史趋势记录和摄像头快照路径"""
    state["sensor_data"] = read_sensors()

    # 注入最近10条历史数据，让 AI 具备趋势感知能力
    state["history"] = get_latest(10)

    # 找最新快照文件
    snapshots = sorted(SNAPSHOT_DIR.glob("*.jpg"))
    state["image_path"] = str(snapshots[-1]) if snapshots else None

    log.info(f"[感知] 传感器: {state['sensor_data']}")
    log.info(f"[感知] 历史记录: {len(state['history'])} 条")
    log.info(f"[感知] 使用快照: {state['image_path']}")
    return state


def decide_node(state: HoujiState) -> HoujiState:
    """调用 Gemini 多模态进行决策，强制结构化输出"""
    # 构造 Prompt
    sensor_text = json.dumps(state["sensor_data"], ensure_ascii=False, indent=2)
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    strategy_text = f"""
【种植与控制策略补充（卧室静音模式 & 视觉动态施肥）】
1. 当前系统时间：{current_time_str} (24小时制)。
2. 光照策略：设定白天为 {LIGHT_ON_HOUR}:00 到 {LIGHT_OFF_HOUR}:00。如果在规定白天时间内请保持灯常亮，夜间休息期务必关闭。
3. 卧室静音打氧策略（继电器7，极其重要）：
   - 【夜间禁止】：为了不影响睡眠，夜间（{LIGHT_OFF_HOUR}:00 到次日 {LIGHT_ON_HOUR}:00），绝对禁止常规轮询开启打氧泵！
   - 【白天低频】：白天期间，仅在每小时的前5分钟内（例如当前分钟数在 00~05 之间）开启打氧泵 60 秒。其余时间保持安静。
4. 视觉动态施肥策略（蠕动泵，继电器1）：
   - 必须先通过摄像头快照判断生菜当前的生长阶段。
   - 参考目标（当前传感器 `ec` 字段数值单位为 μS/cm，直接对齐官方说明书）：
     (1) 育苗期 (三四片真叶)：目标 EC 600 ~ 1000
     (2) 生长期 (旺盛生长)：目标 EC 1000 ~ 1500
     (3) 成熟期 (采摘前)：目标 EC 1300 ~ 1800
   - 【极其严格的防烧苗铁律】：10 升水箱水少但母液极浓！如果你检测到 EC 低于目标下限，控制继电器1（蠕动泵）补液时，`duration_seconds` **必须严格限制在 1 到 3 秒之间**！宁可“蚂蚁搬家”、多等几个5分钟的巡检周期，也绝不允许一次开5秒以上导致浓度暴增烧苗！
   - 【强制联动搅拌】：无论白天还是深夜，只要你决定开启继电器1加液，你都必须**同时下发开启继电器7（打氧泵）60 秒的指令**！利用气泡的翻滚充当搅拌机，确保营养液迅速融开，防止局部浓度过高烧根。
5. 进排气风扇联动通风策略（继电器2=进气, 继电器3=排气，极其重要）：
   - 【强制联动】：进气扇（relay_id=2）与排气扇（relay_id=3）必须同时开、同时关，严禁只开其中一个。
     每次下发通风动作时，actions 列表中必须同时包含 relay_id=2 和 relay_id=3 两条指令。
   - 【触发条件】：仅在满足以下任一条件时才允许通风：
     (1) CO2 浓度 > 1200 ppm（废气积累过高）
     (2) 温度 > 28°C（帐篷过热需降温）
     其他情况禁止开启风扇，保持密闭帐篷的温湿度稳定。
   - 【通风时长】：每次通风 `duration_seconds` 固定设为 120 秒（2分钟）。
     **绝对禁止将风扇设为 duration_seconds=0（持续通风）**，否则帐篷长期漏气会导致温湿度崩溃。
   - 【夜间静音限制】：夜间（{LIGHT_OFF_HOUR}:00 到次日 {LIGHT_ON_HOUR}:00）禁止常规轮询通风。
     仅当 CO2 > 2000 ppm（严重超标危险阈值）时，才允许破例开启一次 120 秒通风。
"""

    # 格式化历史趋势数据（最新在前，便于 AI 感知 EC/CO2/温湿度走势）
    history_lines = []
    for row in state.get("history", []):
        ts = datetime.fromtimestamp(row["timestamp"]).strftime("%m-%d %H:%M")
        history_lines.append(
            f"  [{ts}] "
            f"temp={row.get('temp')}°C  humi={row.get('humidity')}%  "
            f"co2={row.get('co2')}ppm  ec={row.get('ec')}μS/cm"
        )
    history_text = "\n".join(history_lines) if history_lines else "  （暂无历史数据）"

    content = [
        {"type": "text", "text": (
            f"{SYSTEM_PROMPT}\n\n"
            f"当前传感器数据：\n{sensor_text}\n\n"
            f"近期历史趋势（最新在前，共 {len(history_lines)} 条，用于判断 EC/CO2/温湿度走势）：\n"
            f"{history_text}\n\n"
            f"{strategy_text}"
        )}
    ]
    
    # 如果有摄像头图像，则追加
    if state["image_path"] and Path(state["image_path"]).exists():
        import base64
        with open(state["image_path"], "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
        })
    
    decision: HoujiDecision = _llm.invoke([HumanMessage(content=content)])
    
    state["thought"] = decision.thought
    state["actions"] = [a.model_dump() for a in decision.actions]
    log.info(f"[决策] 思考: {decision.thought}")
    log.info(f"[决策] 动作: {state['actions']}")
    return state


def execute_node(state: HoujiState) -> HoujiState:
    """通过 SerialBridge 向 Pico 下发指令，执行继电器动作

    定时动作（duration_seconds > 0）：所有继电器并发计时，互不阻塞。
    总等待时间 = max(duration)，而非各 duration 之和。
    """
    import time
    import threading
    global _bridge
    if _bridge is None:
        _bridge = SerialBridge()

    # 硬性上限：蠕动泵≤30s，进排气扇≤300s（单次通风最多5分钟），其他≤300s
    MAX_DURATION = {1: 30, 2: 300, 3: 300}

    def _auto_off(rid: int, delay: float):
        """在后台线程中等待 delay 秒后关闭指定继电器"""
        time.sleep(delay)
        _bridge.send_command({"cmd": "relay", "id": rid, "state": 0})
        log.info(f"[执行] 继电器{rid} 定时到期，自动关闭")

    results = []
    timers = []
    max_duration = 0

    for action in state["actions"]:
        rid      = action["relay_id"]
        st       = action["state"]
        duration = action.get("duration_seconds", 0)

        # 截断超长 duration
        if duration > 0:
            duration = min(duration, MAX_DURATION.get(rid, 300))
            action = {**action, "duration_seconds": duration}

        # 下发开/关指令
        cmd  = {"cmd": "relay", "id": rid, "state": st}
        resp = _bridge.send_command(cmd)
        log.info(f"[执行] 继电器{rid} => {'ON' if st else 'OFF'}, 回执: {resp}")

        # 定时模式：启动后台线程自动关闭，不阻塞主流程
        if st == 1 and duration > 0:
            t = threading.Thread(target=_auto_off, args=(rid, duration), daemon=True)
            t.start()
            timers.append((t, duration))
            max_duration = max(max_duration, duration)
            log.info(f"[执行] 继电器{rid} 将在 {duration}s 后自动关闭（后台线程）")
            resp = {"on": resp, "duration_s": duration, "auto_off": "pending"}

        results.append({"action": action, "resp": resp})

    # 等待所有定时线程完成（最长 = max duration，而非各 duration 之和）
    if timers:
        log.info(f"[执行] 等待所有定时动作完成，最长 {max_duration}s ...")
        for t, _ in timers:
            t.join()
        log.info("[执行] 所有定时继电器已自动关闭")

    state["results"] = results
    return state


def log_node(state: HoujiState) -> HoujiState:
    """将 AI 思考过程追记到 thought.log"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(THOUGHT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{ts}]\n")
        f.write(f"传感器: {json.dumps(state['sensor_data'], ensure_ascii=False)}\n")
        f.write(f"快照: {state['image_path']}\n")
        f.write(f"思考: {state['thought']}\n")
        f.write(f"动作: {json.dumps(state['actions'], ensure_ascii=False)}\n")
        f.write(f"回执: {json.dumps(state['results'], ensure_ascii=False)}\n")
    return state


# ── 构建 LangGraph ───────────────────────────────────────
def _build_graph():
    builder = StateGraph(HoujiState)
    builder.add_node("sense", sense_node)
    builder.add_node("decide", decide_node)
    builder.add_node("execute", execute_node)
    builder.add_node("log", log_node)
    
    builder.set_entry_point("sense")
    builder.add_edge("sense", "decide")
    builder.add_edge("decide", "execute")
    builder.add_edge("execute", "log")
    builder.add_edge("log", END)
    
    return builder.compile()

_graph = _build_graph()

# ── 对外接口 ─────────────────────────────────────────────
def run_cycle():
    """执行一次完整的 感知→决策→执行→日志 闭环"""
    init_state: HoujiState = {
        "sensor_data": {},
        "history": [],
        "image_path": None,
        "thought": "",
        "actions": [],
        "results": [],
    }
    _graph.invoke(init_state)
