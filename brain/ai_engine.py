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

# 绕过代理的 SSL 拦截（开发环境使用代理时需要）
os.environ.setdefault("GRPC_DEFAULT_SSL_TARGET_NAME_OVERRIDE", "")
os.environ["SSL_CERT_FILE"] = ""
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from config import (
    GEMINI_API_KEY, GEMINI_FLASH_MODEL,
    THOUGHT_LOG_PATH, SNAPSHOT_DIR
)
from sensor_logger import read_sensors, get_latest
from serial_bridge import SerialBridge

log = logging.getLogger("houji.ai")

# 全局串口桥接，避免每次 cycle 重复创建
_bridge: SerialBridge | None = None

# ── Pydantic 结构化输出定义 ──────────────────────────────
class RelayAction(BaseModel):
    relay_id: int   # 继电器编号 1-8
    state: int      # 1=开, 0=关

class HoujiDecision(BaseModel):
    thought: str                 # AI 推理过程
    actions: list[RelayAction]   # 要执行的继电器动作列表

# ── 系统提示词 ───────────────────────────────────────────
SYSTEM_PROMPT = """你是"后稷"，一个专业的水培生菜 AI 农场主。
你正在守护一个 50x50x100cm 密闭帐篷中的两株水培生菜。

你的可控设备（通过继电器 relay_id 控制）：
- relay_id=1 : 营养液蠕动泵 (12V) - 给根部泵送养液
- relay_id=2 : 进气风扇 (12V) - 吸入新鲜空气
- relay_id=3 : 出气风扇 (12V) - 排出废气
- relay_id=7 : 打氧泵 (220V) - 给营养液增氧
- relay_id=8 : 补光灯 (220V) - 全光谱生长光

生长参数参考：
- 温度：18~28°C
- 湿度：60%+
- CO2：800~1200ppm 最佳（过高需通风）
- EC：1.0~2.0 mS/cm（待接入）
- pH：5.5~6.5（待接入）

请根据当前传感器数据与摄像头图像，给出你的分析判断，并给出需要执行的动作列表。
只列出需要变化的状态，不需要变化的设备不必提及。"""

# ── LangGraph State ──────────────────────────────────────
class HoujiState(TypedDict):
    sensor_data: dict
    image_path: str | None
    thought: str
    actions: list[dict]
    results: list[dict]


# ── 节点函数 ─────────────────────────────────────────────

def sense_node(state: HoujiState) -> HoujiState:
    """读取最新传感器数据和摄像头快照路径"""
    state["sensor_data"] = read_sensors()
    
    # 找最新快照文件
    snapshots = sorted(SNAPSHOT_DIR.glob("*.jpg"))
    state["image_path"] = str(snapshots[-1]) if snapshots else None
    
    log.info(f"[感知] 传感器: {state['sensor_data']}")
    log.info(f"[感知] 使用快照: {state['image_path']}")
    return state


def decide_node(state: HoujiState) -> HoujiState:
    """调用 Gemini 多模态进行决策，强制结构化输出"""
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_FLASH_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,
    ).with_structured_output(HoujiDecision)

    # 构造 Prompt
    sensor_text = json.dumps(state["sensor_data"], ensure_ascii=False, indent=2)
    content = [
        {"type": "text", "text": f"{SYSTEM_PROMPT}\n\n当前传感器数据：\n{sensor_text}"}
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
    
    decision: HoujiDecision = llm.invoke([HumanMessage(content=content)])
    
    state["thought"] = decision.thought
    state["actions"] = [a.model_dump() for a in decision.actions]
    log.info(f"[决策] 思考: {decision.thought}")
    log.info(f"[决策] 动作: {state['actions']}")
    return state


def execute_node(state: HoujiState) -> HoujiState:
    """通过 SerialBridge 向 Pico 下发指令，执行继电器动作"""
    global _bridge
    if _bridge is None:
        _bridge = SerialBridge()
    
    results = []
    for action in state["actions"]:
        cmd = {"cmd": "relay", "id": action["relay_id"], "state": action["state"]}
        resp = _bridge.send_command(cmd)
        results.append({"action": action, "resp": resp})
        log.info(f"[执行] 继电器{action['relay_id']} => {'ON' if action['state'] else 'OFF'}, 回执: {resp}")
    
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
        "image_path": None,
        "thought": "",
        "actions": [],
        "results": [],
    }
    _graph.invoke(init_state)
