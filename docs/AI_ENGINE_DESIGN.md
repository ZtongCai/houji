# AI 中枢架构设计：LangGraph 决策引擎

## 1. 为什么选 LangGraph，而不是规则引擎？

传统的自动化农业控制系统依赖硬编码的规则，例如 `if temp > 28: fan_on()`。
这种方式的核心局限在于：规则是人类写的，边界情况很难穷举，而且无法理解"图像中叶片发黄"这样的多模态语义信号。

后稷采用了完全不同的控制哲学：**把所有感知数据和图像送给大模型，让 AI 自己推理，自己决策，直接下达指令。**
大模型（Gemini）既能理解传感器数值，又能"看懂"摄像头照片，因此实现了真正的端到端农业智能体。

为此，我们选用 **LangGraph** 框架来实现这个 AI 闭环，而不是简单的 LangChain Chain，原因如下：

| 对比项 | LangChain Chain | LangGraph |
|---|---|---|
| 执行结构 | 线性一次性 | **循环图结构**，天然适配每天N次的巡检循环 |
| 状态管理 | 手动维护 | **TypedDict State** 贯穿全图，自动流转 |
| RAG 接入点 | 需要大量改造 | **Conditional Edge** 条件路由，可无缝插入 LightRAG |
| 可观测性 | 弱 | 内置节点级 Tracing，AI 思路全记录 |

---

## 2. 图结构设计

```
┌─────────────────────────────────────────────────────┐
│                  LangGraph 决策图                     │
│                                                       │
│  ┌─────────────┐     ┌──────────────┐                │
│  │ sense_node  │────▶│ decide_node  │                │
│  │             │     │              │                │
│  │ • 读传感器  │     │ • Gemini API │                │
│  │ • 取最新快照│     │ • 传感器数据 │                │
│  └─────────────┘     │ • 摄像头图片 │                │
│                      │ • 结构化输出 │                │
│                      └──────┬───────┘                │
│                             │                        │
│                      ┌──────▼───────┐                │
│                      │ execute_node │                │
│                      │              │                │
│                      │ • SerialBridge               │
│                      │ • Pico → 继电器              │
│                      └──────┬───────┘                │
│                             │                        │
│                      ┌──────▼───────┐                │
│                      │   log_node   │                │
│                      │              │                │
│                      │ • thought.log│                │
│                      └──────┬───────┘                │
│                             │                        │
│                           [END]                      │
└─────────────────────────────────────────────────────┘
```

每次调用 `run_cycle()` 函数时，会驱动这张图完整运行一遍，代替了原来主循环中的 `TODO: AI决策`。

---

## 3. 全局状态 (State)

LangGraph 的所有节点共享一个 `TypedDict`，数据无需手动传参：

```python
class HoujiState(TypedDict):
    sensor_data: dict        # 当前传感器读数（实时）
    history: list[dict]      # 最近10条历史数据（趋势感知，已接入）
    image_path: str | None   # 最新快照的文件路径
    thought: str             # Gemini 的推理文字
    actions: list[dict]      # 要执行的继电器指令列表
    results: list[dict]      # Pico 执行后的回执列表
```

> `history` 字段在 `sense_node` 中由 `get_latest(10)` 填充，以时间戳单行格式注入 Prompt，让 AI 能感知 EC/CO₂/温湿度的变化趋势，而非仅凭当前一帧数据决策。

---

## 4. AI 输出格式约束 (Pydantic)

Gemini 被要求以严格的 JSON 结构返回，通过 Pydantic 模型强制校验，彻底消除幻觉或格式错误：

```python
class RelayAction(BaseModel):
    relay_id: int            # 1-8 继电器编号
    state: int               # 1=开, 0=关
    duration_seconds: int = 0  # >0 定时自动关闭；0 持续到下次决策

class HoujiDecision(BaseModel):
    thought: str               # AI 的分析推理
    actions: list[RelayAction] # 要执行的动作
```

**安全约束（硬编码上限）**：

| 设备 | relay_id | MAX_DURATION | 附加规则 |
|---|---|---|---|
| 营养液蠕动泵 | 1 | ≤30s | Prompt 层要求 1~3s；强制联动打氧泵 60s |
| 进气风扇 | 2 | ≤300s | 必须与排气扇（3）同时开关；固定通风 120s；禁止 duration=0 |
| 出气风扇 | 3 | ≤300s | 必须与进气扇（2）同时开关；夜间仅 CO2>2000ppm 时破例 |
| 打氧泵 | 7 | ≤300s | 夜间禁止常规开启；白天每小时前5分钟开60s |
| 补光灯 | 8 | 无限制 | duration_seconds=0 持续；白天常亮，夜间关 |


---

## 5. 设备映射表（继电器 ↔ 外设）

| relay_id | 设备 | 电压层 |
|---|---|---|
| 1 | 营养液蠕动泵 | 12V |
| 2 | 进气风扇 | 12V |
| 3 | 出气风扇 | 12V |
| 4、5、6 | 预留（隔离带） | — |
| 7 | 打氧泵 | 220V |
| 8 | 补光灯 | 220V |

---

## 6. 对外接口

这套引擎对外只暴露一行简洁的调用接口，直接在 `main.py` 的主循环中替换 AI 决策的 TODO 块：

```python
from ai_engine import _graph

init_state = {"sensor_data": {}, "history": [], "image_path": None, "thought": "", "actions": [], "results": []}

# 流式逐节点输出（测试用）
for event in _graph.stream(init_state, stream_mode="updates"):
    ...

# 生产模式
from ai_engine import run_cycle
run_cycle()
```

---

## 7. 架构演进路线

### 当前定位：编排式 Agent（Orchestration Mode）

后稷目前是 LangGraph **线性编排**形态：图结构由程序员预定义，AI 只在 `decide_node` 参与一次，输出结构化 JSON 由 `execute_node` 解析执行。AI 是"决策引擎"而非完全自主 Agent。

```
当前：sense → decide → execute → log → END
        （固定路径，AI 无法改变流程）
```

---

### Phase 3：LightRAG 长期记忆（条件分支路由）

**目标**：让 AI 在发现异常时，能检索历史水培知识库做二次决策，并每日写入生长日记积累经验。

```
decide_node ─── (判定: 叶片异常/疑难) ───▶ rag_node ───▶ decide_node (二次决策)
            └── (判定: 正常) ──────────────▶ execute_node
```

- `rag_node`：从 LightRAG 向量库检索相关水培手册知识
- 检索结果注入 State，丰富 `decide_node` 的上下文
- `rag_memory.py` 中 `insert_diary()` / `query()` 接口已预留

**依赖**：`lightrag-hku`（已在 `requirements.txt` 注释备用）

---

### Phase 4：事件驱动（异常阈值主动触发）

**目标**：突破 5 分钟被动轮询，异常时秒级响应。

`main.py` 增加后台异常监控线程，任一阈值超标立即插队调用 `run_cycle()`：

```python
ALERT_THRESHOLDS = {
    "co2":  2000,   # ppm，严重积累
    "temp": 30.0,   # °C，过热危险
    "ec":   2500,   # μS/cm，烧苗风险
}
```

---

### Phase 5：ReAct Tool Use（完全自主 Agent）

**目标**：AI 从"填表员"升级为"主动调用工具的智能体"，自主决定何时用什么工具，支持多轮推理。

核心操作封装为 LangGraph Tool：

```python
@tool
def read_sensor_history(n: int) -> str:
    """查询最近n条传感器历史，感知趋势"""

@tool
def control_relay(relay_id: int, state: int, duration_seconds: int) -> str:
    """控制指定继电器，返回执行结果"""

@tool
def take_snapshot() -> str:
    """主动拍摄当前摄像头快照"""
```

图结构改为循环 ReAct 模式，AI 自主决定何时停止：

```
agent_node ──▶ tool_node ──▶ observe_node ──┐
    ▲                                        │
    └────────────── (继续推理) ───────────────┘
                        │（任务完成）
                        ▼
                   log_node ──▶ END
```

> ⚠️ **升级风险**：AI 可能在单次周期内多次触发继电器，需要工具层加入计数限制和冷却时间保护。建议硬件稳定运行后再推进。

---

### 演进总览

| 阶段 | 架构类型 | AI 角色 | 状态 |
|---|---|---|---|
| Phase 1~2 | 线性编排 + 历史趋势注入 | 填表决策员（有趋势感知） | ✅ 已完成 |
| Phase 3 | 条件分支 + LightRAG | 知识检索专家 | 🔲 待开发 |
| Phase 4 | 事件驱动 + 异常插队 | 主动响应者 | 🔲 待开发 |
| Phase 5 | ReAct Tool Use | 完全自主智能体 | 🔲 长期目标 |

---

## 8. 依赖安装

```bash
# 在树莓派 Pi5 上执行
pip install langgraph langchain-google-genai pydantic

# Phase 3 接入时追加
# pip install lightrag-hku
```

