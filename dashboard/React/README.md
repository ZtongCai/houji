<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# 后稷农场 · React 看板

星露谷物语风格的水培生菜 AI 实时监控看板，接入 Gemini 决策引擎的真实传感器数据与 AI 思考日志。

## 架构说明

```
bridge.py (FastAPI :8001)  ←  读取 Z盘 SQLite + thought.log
         ↑
Vite Dev Server (:3000)    ←  /api/* 代理到 :8001
         ↑
React App                  ←  每 30s/60s 轮询真实数据
```

## 启动方法

**前置条件：** Node.js、Python 3（conda main 环境）、已挂载 Samba Z: 盘

### 第 1 步：启动数据桥接后端

打开**第一个终端**：

```powershell
cd z:\dashboard\React
pip install -r requirements.txt
uvicorn bridge:app --port 8001 --reload
```

看到 `Application startup complete.` 即可。

### 第 2 步：启动 React 前端

打开**第二个终端**：

```powershell
cd z:\dashboard\React
npm install
npm run dev
```

浏览器访问 `http://localhost:3000` 即可看到带真实数据的极客风看板。

## 接口说明

| 接口 | 说明 |
|---|---|
| `GET /api/sensors` | 最新一条传感器读数（来自 `houji.db`）|
| `GET /api/thoughts` | 最近 20 轮 AI 决策周期（来自 `thought.log`）|

## 数据刷新频率

- 传感器数据：**每 30 秒**自动刷新
- AI 思考日志：**每 60 秒**自动刷新
