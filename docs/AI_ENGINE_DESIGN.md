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
    sensor_data: dict        # 当前传感器读数
    image_path: str | None   # 最新快照的文件路径
    thought: str             # Gemini 的推理文字
    actions: list[dict]      # 要执行的继电器指令列表
    results: list[dict]      # Pico 执行后的回执列表
```

---

## 4. AI 输出格式约束 (Pydantic)

Gemini 被要求以严格的 JSON 结构返回，通过 Pydantic 模型强制校验，彻底消除幻觉或格式错误：

```python
class RelayAction(BaseModel):
    relay_id: int   # 1到8的继电器编号
    state: int      # 1=开, 0=关

class HoujiDecision(BaseModel):
    thought: str               # AI的分析推理
    actions: list[RelayAction] # 要执行的动作
```

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
from ai_engine import run_cycle

# 主循环中
if now - last_ai >= AI_DECISION_INTERVAL:
    run_cycle()
```

---

## 7. 未来扩展：Phase 2 的 LightRAG 接入点

在 `decide_node` 中增加一个条件分支路由器：
- 当 AI 发现"疑难杂症"（如识别到叶片异色、根茎腐烂迹象），可以自动路由到 `rag_node`
- `rag_node` 从 LightRAG 向量库检索相关的水培手册知识
- 将检索结果注入 State，交回 `decide_node` 用丰富上下文做二次决策

```
decide_node ─── (判定: 异常) ───▶ rag_node ───▶ decide_node (二次)
            └── (判定: 正常) ───▶ execute_node
```

---

## 8. 依赖安装

```bash
# 在树莓派 Pi5 上执行
pip install langgraph langchain-google-genai pydantic
```
