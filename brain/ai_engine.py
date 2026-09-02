"""AI 决策中枢：感知 → 决策 → 执行 → 记录。"""
import json
import math
import logging
from datetime import datetime
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from config import (
    THOUGHT_LOG_PATH, SNAPSHOT_DIR,
    LIGHT_ON_HOUR, LIGHT_OFF_HOUR,
    DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, QWEN_MODEL,
    CROP_NAME, CROP_PROFILE_NAME, GROWTH_STAGE,
    NUTRIENT_PRODUCT, EC_TARGETS, CURRENT_GROWTH_STAGE,
    EC_TARGET_MIN, EC_TARGET_MAX, NUTRIENT_DOSING_ENABLED,
    CONTROL_ENABLED, RUN_MODE
)
from sensor_logger import read_sensors, get_latest
from serial_bridge import SerialBridge

log = logging.getLogger("houji.ai")


# ── Pydantic 结构化输出定义 ──────────────────────────────
class RelayAction(BaseModel):
    relay_id: Literal[1, 2, 3, 7, 8]
    state: Literal[0, 1]
    duration_seconds: int = Field(default=0, ge=0, le=300)

class HoujiDecision(BaseModel):
    thought: str                 # AI 推理过程
    actions: list[RelayAction]   # 要执行的继电器动作列表



# ── 系统提示词 ───────────────────────────────────────────
SYSTEM_PROMPT = f"""你是"后稷"，一个专业的水培{CROP_NAME} AI 农场主。
你正在守护一个 50x50x100cm 密闭帐篷中的水培{CROP_NAME}。
当前作物配置：{CROP_PROFILE_NAME}；人工指定阶段：{GROWTH_STAGE}（{CURRENT_GROWTH_STAGE['label']}）；运行模式：{RUN_MODE}。

你的可控设备（通过继电器 relay_id 控制）：
- relay_id=1 : 营养液蠕动泵 (12V) - 给水箱添加营养液
- relay_id=2 : 进气风扇 (12V) - 吸入新鲜空气
- relay_id=3 : 出气风扇 (12V) - 排出废气
- relay_id=7 : 打氧泵 (220V) - 给营养液增氧
- relay_id=8 : 补光灯 (220V) - 全光谱生长光

【重要】动作字段说明：
- state=1/0 表示开/关
- duration_seconds：
  - 营养液泵（relay_id=1）：仅在配置允许时才可开启；系统强制固定为 10 秒
  - 打氧泵（relay_id=7）：必须设 duration_seconds，范围 10~120s
  - 风扇（relay_id=2,3）：通风场景设 duration_seconds（如 60~300s），持续通风设 0
  - 补光灯（relay_id=8）：设 duration_seconds=0，持续开启到下次决策

生长参数参考：
- 温度：18~28°C
- 湿度：60%+
- CO2：800~1200ppm 最佳（过高需通风）
- 当前阶段 EC：{EC_TARGET_MIN:.0f}~{EC_TARGET_MAX:.0f} μS/cm
- pH：5.5~6.5（待接入）

请根据当前传感器数据与摄像头图像，给出分析判断和需要执行的动作列表。
阶段由配置人工指定，禁止根据图像自行切换阶段。只列出需要变化的设备。"""

# ── 决策状态 ─────────────────────────────────────────────
class HoujiState(TypedDict):
    sensor_data: dict
    history: list[dict]    # 最近N条历史传感器数据，用于趋势判断
    image_path: str | None
    thought: str
    actions: list[dict]
    results: list[dict]
    model_used: str


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
    """调用阿里云百炼 qwen3.7-plus 进行文本决策并强制结构化输出。"""
    # 构造 Prompt
    sensor_text = json.dumps(state["sensor_data"], ensure_ascii=False, indent=2)
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ec_stage_text = "\n".join(
        f"     - {stage['label']}：EC {stage['min']:.0f} ~ {stage['max']:.0f} μS/cm"
        + (f"，标签兑水比例 {stage['dilution']}" if stage.get("dilution") else "")
        for stage in EC_TARGETS.values()
    )
    dosing_policy = (
        "自动加液已启用：只有有效 EC 低于当前阶段下限时，才允许继电器1固定运行10秒。"
        if NUTRIENT_DOSING_ENABLED else
        "自动加液当前禁用：禁止下发任何 relay_id=1、state=1 的动作。"
    )

    strategy_text = f"""
【种植与控制策略补充（卧室静音模式 & 厂家 EC 分阶段配置）】
1. 当前系统时间：{current_time_str} (24小时制)。
2. 当前作物：{CROP_NAME}；当前阶段由人工配置为 {GROWTH_STAGE}（{CURRENT_GROWTH_STAGE['label']}），禁止通过图片自行切换阶段。
3. 光照策略：设定白天为 {LIGHT_ON_HOUR}:00 到 {LIGHT_OFF_HOUR}:00。如果在规定白天时间内请保持灯常亮，夜间休息期务必关闭。
4. 卧室静音打氧策略（继电器7）：
   - 夜间（{LIGHT_OFF_HOUR}:00 到次日 {LIGHT_ON_HOUR}:00）禁止常规轮询开启打氧泵。
   - 白天光照期间，每次决策开启打氧泵 60 秒，由底层定时关闭。
5. 营养液与 EC 策略（继电器1）：
   - 产品：{NUTRIENT_PRODUCT}。EC 单位为 μS/cm，目标来自用户提供的厂家标签：
{ec_stage_text}
   - 当前阶段目标：{EC_TARGET_MIN:.0f} ~ {EC_TARGET_MAX:.0f} μS/cm。
   - 厂家兑水比例只作为人工配液参考，不得直接换算成泵运行时间；A/B 两液投加管路尚未确认。
   - {dosing_policy}
   - 若允许加液并确需补液，duration_seconds 必须固定为 10 秒，同时开启继电器7打氧 60 秒用于混合。
6. 进排气风扇联动通风策略（继电器2=进气, 继电器3=排气）：
   - 进气扇与排气扇必须同时开、同时关。
   - 仅在 CO2 > 1200 ppm 或温度 > 28°C 时允许通风，每次固定 120 秒，禁止持续通风。
   - 夜间仅当 CO2 > 2000 ppm 时允许破例通风 120 秒。
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

    # 摄像头快照仅保存在本地；Qwen 默认只接收传感器与历史文本，不外发图片。

    # ── 唯一模型：阿里云百炼 qwen3.7-plus ─────────────────
    decision = None
    last_error = ""
    try:
        from openai import DefaultHttpxClient, OpenAI

        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
            http_client=DefaultHttpxClient(timeout=60.0, trust_env=False),
        )
        text_prompt = (
            content[0]["text"]
            + '\n\n【格式强制】你必须只能输出纯 JSON 数据，禁止包含其他字符：'
            + '{"thought":"推理分析","actions":[{"relay_id":1,"state":0,"duration_seconds":0}]}'
        )
        log.info(f"[决策] 直连阿里云百炼模型: {QWEN_MODEL}")
        resp = client.chat.completions.create(
            model=QWEN_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            extra_body={"enable_thinking": False},
            messages=[
                {
                    "role": "system",
                    "content": "你是后稷农业决策模型，只能以 JSON 格式输出响应。",
                },
                {"role": "user", "content": text_prompt},
            ],
        )
        raw_text = (resp.choices[0].message.content or "").strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```")[-1].split("```")[0].strip()

        parsed = json.loads(raw_text)
        actions = [RelayAction(**a) for a in parsed.get("actions", [])]
        decision = HoujiDecision(
            thought=parsed.get("thought", "Qwen 分析完成"),
            actions=actions,
        )
        state["model_used"] = QWEN_MODEL
        log.info(f"[决策] 阿里云百炼 {QWEN_MODEL} 响应成功")
    except Exception as qwen_e:
        last_error = str(qwen_e)
        log.error(f"[决策] 阿里云百炼 {QWEN_MODEL} 调用失败: {last_error}")
    if decision is None:
        state["thought"] = f"Qwen 决策不可用，最近错误：{last_error}"
        state["actions"] = []
        state["model_used"] = "None"
        return state

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
    results = []

    # 总安全门必须在创建 SerialBridge 之前执行，observe 模式不接触 Pico。
    if not CONTROL_ENABLED:
        for action in state.get("actions", []):
            results.append({
                "action": action,
                "resp": None,
                "blocked": True,
                "reason": f"RUN_MODE={RUN_MODE}",
            })
        if state.get("actions"):
            log.warning(f"[安全] {RUN_MODE} 模式拦截 {len(state['actions'])} 个继电器动作")
        state["results"] = results
        return state

    bridge = SerialBridge()

    # 硬性上限：蠕动泵固定≤10s，进排气扇≤300s，其他≤300s
    MAX_DURATION = {1: 10, 2: 300, 3: 300}

    for action in state["actions"]:
        rid      = action["relay_id"]
        st       = action["state"]
        duration = action.get("duration_seconds", 0)

        # 营养液泵采用确定性门控，不能只依赖模型提示词。
        if rid == 1 and st == 1:
            ec_value = state.get("sensor_data", {}).get("ec")
            block_reason = None
            if not NUTRIENT_DOSING_ENABLED:
                block_reason = "NUTRIENT_DOSING_ENABLED=false"
            elif (
                isinstance(ec_value, bool)
                or not isinstance(ec_value, (int, float))
                or not math.isfinite(float(ec_value))
                or ec_value <= 0
            ):
                block_reason = f"EC 无效: {ec_value!r}"
            elif ec_value >= EC_TARGET_MIN:
                block_reason = (
                    f"EC={ec_value} 未低于当前阶段下限 {EC_TARGET_MIN:.0f} μS/cm"
                )

            if block_reason:
                log.warning(f"[安全] 拦截营养液泵动作: {block_reason}")
                results.append({
                    "action": action,
                    "resp": None,
                    "blocked": True,
                    "reason": block_reason,
                })
                continue

            duration = 10
            action = {**action, "duration_seconds": duration}

        # 截断超长 duration
        if duration > 0:
            duration = min(duration, MAX_DURATION.get(rid, 300))
            action = {**action, "duration_seconds": duration}

        # 下发开/关指令，把 duration 下放给 Pico 硬件！
        if st == 1 and duration > 0:
            cmd  = {"cmd": "relay", "id": rid, "state": st, "duration": duration}
        else:
            cmd  = {"cmd": "relay", "id": rid, "state": st}

        resp = bridge.send_command(cmd)
        ack_ok = bool(
            resp
            and resp.get("status") == "ok"
            and resp.get("id") == rid
        )
        log.info(f"[执行] 继电器{rid} => {'ON' if st else 'OFF'}, 回执: {resp}")
        if not ack_ok:
            results.append({
                "action": action,
                "resp": resp,
                "failed": True,
                "reason": "未收到与指令匹配的 Pico 成功回执",
            })
            log.error(f"[安全] 继电器{rid} 指令未确认，禁止记录为执行成功")
            continue

        # === 核心修复：防浪涌欠压复位缓冲 ===
        # 等待 1.5 秒，让电容回充和供电电压稳定，错峰下发下一个强电设备
        time.sleep(1.5)

        # 把前台日志追记放在这里，并且彻底废除 _auto_off 死磕线程
        if st == 1 and duration > 0:
            log.info(f"[执行] 继电器{rid} 将在 {duration}s 后自动关闭（已移交底层硬件守护）")
            results.append({"action": action, "resp": {"on": resp, "duration_s": duration, "auto_off": "hardware"}})
            # 向前台追记状态以抵消打开状态
            try:
                with open(THOUGHT_LOG_PATH, "a", encoding="utf-8") as f:
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"\n{'='*60}\n")
                    f.write(f"[{ts}]\n")
                    f.write("模型: 硬件守护进程\n")
                    f.write(f"思考: 已将定时关闭任务移交 Pico 硬件层。继电器{rid} 将在 {duration} 秒后强制脱机拉闸！\n")
                    f.write(f"动作: [{{\"relay_id\": {rid}, \"state\": 0}}]\n")
            except Exception as e:
                log.error(f"写入硬件守护日志失败: {e}")
        else:
            results.append({"action": action, "resp": resp})

    state["results"] = results
    return state


def log_node(state: HoujiState) -> HoujiState:
    """将一次 AI 决策按 JSON Lines 追记到 thought.log。"""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "sensor_data": state["sensor_data"],
        "image_path": state["image_path"],
        "model": state.get("model_used", "Unknown"),
        "thought": state["thought"],
        "actions": state["actions"],
        "results": state["results"],
    }
    with THOUGHT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return state



# ── 对外接口 ─────────────────────────────────────────────
def run_cycle():
    """执行一次完整的 感知→决策→执行→日志 闭环"""
    state: HoujiState = {
        "sensor_data": {},
        "history": [],
        "image_path": None,
        "thought": "",
        "actions": [],
        "results": [],
    }
    state = sense_node(state)
    state = decide_node(state)
    state = execute_node(state)
    log_node(state)
