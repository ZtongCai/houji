# 后稷 (Project Houji) 🌱

> 一个在 50×50×100cm 密闭帐篷内，由 Gemini AI 全程接管的水培生菜生命周期项目。

## 系统架构

```
[Camera OV5647] ──┐
[7合1环境传感器]──▶  [Pi 5 (brain)] ── USB ──▶ [Pico (spine)] ──▶ 继电器板
                                     Samba ▼                     ├── 营养液蠕动泵 (relay 1)
                                 [Windows 看板]                  ├── 进气风扇 (relay 2)
                                                                 ├── 出气风扇 (relay 3)
                                                                 ├── 打氧泵 (relay 7)
                                                                 └── 补光灯 (relay 8)
```

## 核心技术栈

| 层 | 技术 |
|---|---|
| AI 决策 | LangGraph + Gemini 3 Flash Preview |
| 传感数据 | SQLite (`houji.db`) |
| 摄像头 | picamera2 (OV5647 CSI) |
| 继电器通信 | pyserial · JSON Lines 协议 |
| 长期记忆 | LightRAG (Phase 3，待接入) |
| 看板 | Streamlit (`dashboard/app.py`) |

## 目录结构

```
brain/          # Pi 5 主控（Python）
  ai_engine.py      LangGraph 决策图（sense → decide → execute → log）
  sensor_logger.py  传感器采集 + SQLite 存储
  sensor_reader.py  7合1传感器串口驱动
  serial_bridge.py  Pi5 ↔ Pico 继电器通信
  camera.py         OV5647 快照
  config.py         全局配置（从 .env 加载密钥）
  main.py           主循环（60s 采集 / 5min 快照+决策）
  rag_memory.py     LightRAG 预留接口
  data/             运行时数据（Git 忽略）
    houji.db          传感器历史
    thought.log       AI 决策记录
    houji.log         系统运行日志
    snapshots/        摄像头快照
spine/          # Pico 执行器（MicroPython）
  main.py           串口监听 + JSON 解析
  relay_driver.py   8路继电器驱动（低电平触发）
dashboard/      # Windows 看板
  app.py            Streamlit 三栏看板
test/           # 测试脚本
docs/           # 项目文档
```

## 快速开始

```bash
# Pi5 - 激活环境并启动
source brain/venv/bin/activate
python brain/main.py

# 测试脚本（单独验证各模块）
python test/test_ai_engine.py  # AI 决策闭环（流式输出）
python test/test_camera.py     # 摄像头快照
python test/reset_relays.py    # 全部继电器复位

# Windows 看板
cd dashboard && pip install -r requirements.txt
streamlit run dashboard/app.py
```

> ⚠️ **代理配置**：Pi5 需通过局域网代理访问 Gemini API（已写入 `brain/venv/bin/activate`）

## 数据文件

| 文件 | 内容 |
|---|---|
| `brain/data/houji.db` | 传感器历史（SQLite） |
| `brain/data/thought.log` | AI 每次决策的推理过程 |
| `brain/data/houji.log` | 系统运行日志 |
| `brain/data/snapshots/` | 摄像头定时快照 |

## 文档

- [项目总纲](docs/PROJECT_BRIEF.md)
- [AI 引擎设计](docs/AI_ENGINE_DESIGN.md)
- [Gemini 可用模型](docs/GEMINI_MODELS.md)

## 阶段进展

- ✅ Phase 1：传感器 + 摄像头 + 继电器硬件全链路打通
- ✅ Phase 2：LangGraph + Gemini 3 Flash AI 决策闭环打通（含定时执行安全保护）
- 🔲 Phase 3：LightRAG 长期记忆接入
- 🔲 Phase 4：Streamlit 看板 + OBS 直播

---
*致敬 Sol 模式 🤖*
