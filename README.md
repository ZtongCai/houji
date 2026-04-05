# 后稷 (Project Houji) 🌱

> 一个在 50×50×100cm 密闭帐篷内，由 Gemini AI 全程接管的水培生菜生命周期项目。

## 系统架构

```
[Camera OV5647] ──┐
[7合1传感器]   ──▶  [Pi 5 (brain)] ── USB ──▶ [Pico (spine)] ──▶ 继电器板
                                     Samba ▼                     ├── 营养液泵
                                 [Windows 看板]                  ├── 进/出气风扇
                                                                 ├── 打氧泵
                                                                 └── 补光灯
```

## 核心技术栈

| 层 | 技术 |
|---|---|
| AI 决策 | LangGraph + Gemini 3 Flash Preview |
| 传感数据 | SQLite (`houji.db`) |
| 摄像头 | picamera2 (OV5647 CSI) |
| 继电器通信 | pyserial · JSON Lines 协议 |
| 长期记忆 | LightRAG (Phase 2) |
| 看板 | Streamlit (Phase 3) |

## 快速开始

```bash
# Pi5 - 激活环境并启动
source brain/venv/bin/activate
python brain/main.py

# 常用测试脚本
python test/test_camera.py       # 测试摄像头
python test/test_ai_engine.py    # 测试 AI 决策闭环
python test/reset_relays.py      # 全部继电器复位断开
```

> ⚠️ 需在 Pi5 上设置代理环境变量，以访问 Gemini API：
> `export https_proxy=http://192.168.1.40:8001`

## 数据目录

```
brain/data/
├── houji.db        # 传感器历史数据
├── thought.log     # AI 每次决策的推理记录
└── snapshots/      # 摄像头定时快照
```

## 文档

- [项目总纲](docs/PROJECT_BRIEF.md)
- [AI 引擎设计](docs/AI_ENGINE_DESIGN.md)
- [Gemini 可用模型](docs/GEMINI_MODELS.md)

## 进展

- ✅ Phase 1：传感器 + 摄像头 + 继电器硬件全链路打通
- ✅ Phase 2：LangGraph + Gemini AI 决策闭环打通
- 🔲 Phase 3：Streamlit 看板 + OBS 直播

---
*致敬 Sol 模式 🤖*
