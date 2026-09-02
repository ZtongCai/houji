# AI 中枢设计：顺序决策管线

## 1. 当前原则

阿里云百炼 qwen3.7-plus 接收传感器数值、最近历史和控制策略，返回经过 Pydantic 校验的结构化动作。摄像头照片仅本地保存，不外发。
当前流程固定为四步，普通函数顺序调用已经足够，不需要额外编排框架。

---

## 2. 决策流程

```
┌─────────────────────────────────────────────────────┐
│                    AI 决策管线                        │
│                                                       │
│  ┌─────────────┐     ┌──────────────┐                │
│  │ sense_node  │────▶│ decide_node  │                │
│  │             │     │              │                │
│  │ • 读传感器  │     │ • Qwen API  │                │
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

每次调用 `run_cycle()` 时，依次执行感知、决策、执行和记录。

---

## 3. 全局状态 (State)

四个步骤共享一个 `TypedDict` 状态：

```python
class HoujiState(TypedDict):
    sensor_data: dict        # 当前传感器读数（实时）
    history: list[dict]      # 最近10条历史数据（趋势感知，已接入）
    image_path: str | None   # 最新快照的文件路径
    thought: str             # Qwen 的推理文字
    actions: list[dict]      # 要执行的继电器指令列表
    results: list[dict]      # Pico 执行后的回执列表
```

> `history` 字段在 `sense_node` 中由 `get_latest(10)` 填充，以时间戳单行格式注入 Prompt，让 AI 能感知 EC/CO₂/温湿度的变化趋势，而非仅凭当前一帧数据决策。

---

## 4. AI 输出格式约束 (Pydantic)

Qwen 被要求以严格的 JSON 结构返回，通过 Pydantic 模型强制校验并拒绝非法动作字段：

```python
class RelayAction(BaseModel):
    relay_id: int            # 1-8 继电器编号
    state: int               # 1=开, 0=关
    duration_seconds: int = 0  # >0 定时自动关闭；0 持续到下次决策

class HoujiDecision(BaseModel):
    thought: str               # AI 的分析推理
    actions: list[RelayAction] # 要执行的动作
```

**安全边界**：设备策略与当前执行层硬约束统一维护在 README 的“AI 策略与确定性安全边界”表中，避免两份参数漂移。


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

主循环只调用一个入口：

```python
from ai_engine import run_cycle
run_cycle()
```

---

## 7. 架构演进路线

### 当前架构

`sense_node → decide_node → execute_node → log_node` 顺序执行；执行层继续使用观察模式、动作白名单和时长上限做确定性拦截。

---

### 后续原则

- 长期记忆只有在现有历史窗口不足时再设计，并根据真实数据量选择存储方案。

---

- 只有实测证明定时轮询不够快时，才增加事件触发。

---

- 自主工具调用只有在单次决策确实需要多轮交互时再增加，且不能绕过执行层安全门控。

---

### 演进条件

先用运行数据证明当前方案的缺口，再引入对应复杂度。

---

## 8. 依赖安装

```bash
pip install -r requirements.txt
```

