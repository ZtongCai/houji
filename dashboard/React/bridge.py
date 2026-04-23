"""
后稷数据桥接层 (Windows 端)
读取 Z 盘(Samba) 的 SQLite 和 thought.log，对 React 前端提供 JSON API
启动: uvicorn bridge:app --port 8001 --reload
"""
import json
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许 Vite 开发服务器跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# 自适应数据目录：优先找到含 houji.db 的目录
def find_data_dir() -> Path:
    candidates = [
        Path("Z:/"),
        Path("Z:/brain/data"),
        Path(__file__).parent.parent.parent / "brain" / "data",
    ]
    for d in candidates:
        if d.exists() and (d / "houji.db").exists():
            return d
    return candidates[0]


DATA_DIR = find_data_dir()
DB_PATH = DATA_DIR / "houji.db"
THOUGHT_LOG = DATA_DIR / "thought.log"


@app.get("/api/sensors")
def get_sensors():
    """返回最新一条传感器读数"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return {}
    return dict(row)


@app.get("/api/thoughts")
def get_thoughts():
    """
    解析 thought.log，返回最近 N 个决策周期
    优化：只读取文件末尾部分，避免大文件阻塞
    """
    if not THOUGHT_LOG.exists():
        return []

    try:
        # 只读取末尾 100KB，通常足够容纳 20 条记录
        filesize = THOUGHT_LOG.stat().st_size
        read_size = min(filesize, 102400) 
        
        with open(THOUGHT_LOG, "rb") as f:
            f.seek(filesize - read_size)
            text = f.read().decode("utf-8", errors="ignore")
            
        # 按分隔线切分成若干块
        blocks = re.split(r"={10,}", text)
        entries = []
        idx = 0

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            ts_match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", block)
            thought_match = re.search(r"思考: (.+?)(?=\n动作:|\Z)", block, re.DOTALL)
            actions_match = re.search(r"动作: (\[.+?\])", block, re.DOTALL)

            if not ts_match or not thought_match:
                continue

            actions = []
            if actions_match:
                try:
                    actions = json.loads(actions_match.group(1))
                except:
                    pass

            idx += 1
            entries.append({
                "id": str(idx),
                "timestamp": ts_match.group(1),
                "thought": thought_match.group(1).strip(),
                "actions": actions,
            })

        # 返回最新 20 条（倒序）
        return list(reversed(entries[-20:]))
    except Exception as e:
        print(f"Error reading log: {e}")
        return []
