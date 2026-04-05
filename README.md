# 后稷 (Project Houji) 🌱

> 一个在 50×50×100cm 密闭帐篷内，由 AI 全程接管的水培生菜生命周期项目。

## 架构概览

```
brain/        # 树莓派 5 端：Python 主控 + AI 决策
spine/        # 树莓派 Pico 端：MicroPython 继电器驱动
dashboard/    # Windows 端：Streamlit 直播看板
docs/         # 项目文档
```

## 硬件拓扑

```
[Camera V1.3] ──────┐
                    ▼
[Pi 5 (brain)] ←── USB 串口 ──→ [Pico (spine)] ──→ 继电器板
     │                                               ├── 全光谱补光灯
     │ Samba 共享 (局域网)                            ├── 排气扇
     ▼                                               └── 蠕动泵
[Windows Dashboard]
```

## AI & 数据栈

| 模块 | 技术 | 用途 |
|------|------|------|
| 决策引擎 | Gemini Flash / Pro | 视觉巡检 + 动作指令 |
| 长期记忆 | LightRAG | 水培手册 + 生长日记 |
| 短波记忆 | SQLite | 传感器高频数值 |

## 数据目录（Samba 共享）

```
brain/data/
├── houji.db          # SQLite 传感器数据库
├── thought.log       # AI 思考日志
├── snapshots/        # 摄像头定时快照
└── rag_store/        # LightRAG 向量库 + 图谱
```

## 快速开始

```bash
# Pi 5 端
cd brain && pip install -r requirements.txt
python main.py

# Windows 看板端
cd dashboard && pip install -r requirements.txt
streamlit run app.py
```

## 阶段规划

- **Phase 1 (当前)**：硬件跑通 + 基础生存控制
- **Phase 2**：AI 决策 + LightRAG 接入
- **Phase 3**：Streamlit 看板 + OBS 直播

---
*致敬 Sol 模式 🤖*
