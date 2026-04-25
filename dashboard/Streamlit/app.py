"""
后稷 Pro 看板 v3.0 (Legacy Pixel Edition)
终极修复版：放弃碎片化 st 组件，改用全容器 HTML 渲染，确保样式和日志绝不泄露源码。
"""
import time
import json
import sqlite3
import base64
import streamlit as st
from pathlib import Path
from datetime import datetime

# ── 配置 ──────────────────
def find_data_dir():
    candidates = [
        Path("/home/houjiagent/houji/brain/data"), 
        Path("Z:/brain/data"),      
        Path(__file__).parent.parent.parent / "brain" / "data", 
        Path("./brain/data"),       
    ]
    for d in candidates:
        if d.exists() and (d / "houji.db").exists():
            return d
    return candidates[0]

DATA_DIR = find_data_dir()
DB_PATH      = DATA_DIR / "houji.db"
THOUGHT_LOG  = DATA_DIR / "thought.log"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

st.set_page_config(page_title="HOUJI AI CENTER", layout="wide", initial_sidebar_state="collapsed")

# ── 核心工具 ──────────────────
def img_to_b64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return ""

def load_farm_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1").fetchone()
        if not row: return {}
        cols = [d[0] for d in conn.execute("SELECT * FROM sensor_readings LIMIT 1").description]
        return dict(zip(cols, row))
    except: return {}
    finally: conn.close()

def load_farm_logs():
    if not THOUGHT_LOG.exists(): return []
    try:
        text = THOUGHT_LOG.read_text(encoding="utf-8")
        sections = text.split("============================================================")
        items = []
        for s in reversed(sections):
            s = s.strip()
            if not s or "[" not in s: continue
            lines = s.splitlines()
            ts = s.split("]")[0].replace("[", "").split(" ")[1] if " " in s else "--:--"
            thought, actions, model_name = "", [], "Gemini"
            for l in lines:
                if l.startswith("模型:"): model_name = l.replace("模型:", "").strip()
                elif l.startswith("思考:"): thought = l.replace("思考:", "").strip()
                elif l.startswith("动作:"): 
                    try: actions = json.loads(l.replace("动作:", "").strip())
                    except: actions = []
            items.append({"ts": ts, "type": f"分析 | {model_name}", "content": thought, "color": "#2e5d9b"})
            if actions:
                names = {1: '养液泵', 2: '进风', 3: '出风', 7: '打氧', 8: '补光'}
                msg_parts = []
                for a in actions:
                    r_id = a.get('relay_id', 0)
                    state_str = 'ON' if a.get('state') else 'OFF'
                    name_str = names.get(r_id, f"R{r_id}")
                    msg_parts.append(f"{name_str} {state_str}")
                msg = " | ".join(msg_parts)
                items.append({"ts": ts, "type": "执行", "content": f"指令: {msg}", "color": "#348e3e"})
        return items[:40]
    except: return []

# ── 渲染核心 ──────────────────

# 准备数据
data = load_farm_data()
logs = load_farm_logs()
snaps = sorted(SNAPSHOT_DIR.glob("*.jpg"))
img_b64 = img_to_b64(snaps[-1]) if snaps else ""

# 注入 CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
#MainMenu, header, footer {visibility: hidden;}
.stApp { background-color: #2c1e14; }
.block-container { padding: 1.5rem !important; max-width: 1600px; }

/* 容器定义 */
.p-card {
    background-color: #f4e4bc;
    border: 4px solid #4a2e19;
    box-shadow: 6px 6px 0px rgba(0,0,0,0.4);
    font-family: 'VT323', monospace;
    color: #4a2e19;
    overflow: hidden;
    margin-bottom: 20px;
    height: 100%;
}
.p-header {
    background-color: #8b5a2b;
    border-bottom: 4px solid #4a2e19;
    padding: 6px 15px;
    color: #f4e4bc;
    font-size: 24px;
}
.p-body { padding: 15px; height: calc(100% - 46px); }

/* 传感器盒子 (3列网格) */
.sensor-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; height: 100%; }
.m-box {
    background: rgba(74, 46, 25, 0.1);
    border: 2px solid #4a2e19;
    padding: 10px 15px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}
.m-title { font-size: 16px; font-weight: bold; opacity: 0.8; margin-bottom: 4px; }
.m-val { font-size: 32px; font-weight: bold; line-height: 1.1; display: flex; align-items: baseline; gap: 4px; }
.m-unit { font-size: 16px; opacity: 0.8; font-weight: normal; }

/* 执行器网格 (3列网格排列) */
.act-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.act-cell {
    border: 2px solid #4a2e19;
    padding: 15px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: rgba(255,255,255,0.2);
    font-size: 22px;
    text-align: center;
    gap: 10px;
}
.act-on { background: rgba(255, 204, 51, 0.4); border-color: #ffcc33; }
.act-dot { width: 16px; height: 16px; background: #4a2e19; outline: 2px solid rgba(0,0,0,0.1); }
.act-on .act-dot { background: #ffcc33; box-shadow: 0 0 15px #ffcc33; }

/* 日志框 */
.log-terminal {
    background-color: #fcf5e5;
    height: 420px;
    overflow-y: auto;
    padding: 15px;
}
.log-row { margin-bottom: 15px; border-bottom: 1px solid rgba(0,0,0,0.08); padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# 1. 顶部栏
st.markdown(f"""
<div class="p-card" style="background:#8b5a2b; margin-bottom:25px; height:auto;">
    <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 25px; color:#f4e4bc;">
        <div style="font-size:38px;">🌱 后稷 HOUJI--LLM AI驱动的水培生菜生命周期项目</div>
        <div style="font-size:22px;">
            <span id="live-clock">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span> | 核心: Gemini/Qwen
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

import streamlit.components.v1 as components
components.html("""
<script>
    // 在 iframe 内部获取父级窗口，突破 React 安全限制修改外部 DOM
    const targetDoc = window.parent.document;
    if(window.parent.houjiClockTimer) { clearInterval(window.parent.houjiClockTimer); }
    
    window.parent.houjiClockTimer = setInterval(function() {
        var el = targetDoc.getElementById("live-clock");
        if (el) {
            var now = new Date();
            var y = now.getFullYear();
            var m = String(now.getMonth() + 1).padStart(2, '0');
            var d = String(now.getDate()).padStart(2, '0');
            var h = String(now.getHours()).padStart(2, '0');
            var min = String(now.getMinutes()).padStart(2, '0');
            var s = String(now.getSeconds()).padStart(2, '0');
            el.innerText = y + "-" + m + "-" + d + " " + h + ":" + min + ":" + s;
        }
    }, 1000);
</script>
""", height=0)

# ── 第 1 行：监控 (左) | 日志 (右) ──
r1_c1, r1_c2 = st.columns(2)

with r1_c1:
    # 监控卡片，高度锁定 466px (头部46 + 内容420)
    st.markdown(f"""
    <div class="p-card" style="height: 466px;">
        <div class="p-header">📷 实时视频流</div>
        <div style="background:#000; height:420px; display:flex; justify-content:center; align-items:center;">
            <img src="data:image/jpeg;base64,{img_b64}" style="width:100%; height:100%; object-fit:contain;">
        </div>
    </div>
    """, unsafe_allow_html=True)

with r1_c2:
    # 日志卡片，高度同样锁定 466px
    logs_html = ""
    for it in logs:
        ts = it.get("ts", "")
        ctype = it.get("type", "")
        color = it.get("color", "")
        content = it.get("content", "")
        logs_html += f"<div class='log-row'><div style='font-size:14px; opacity:0.6;'>[{ts}]</div><div style='padding:4px 0;'><span style='color:{color}; font-weight:bold;'>[{ctype}] </span><span style='font-size:18px;'>{content}</span></div></div>"
    
    st.markdown(f"""
    <div class="p-card" style="height: 466px;">
        <div class="p-header">🧠 AI 思考与决策日志</div>
        <div class="log-terminal">{logs_html}</div>
    </div>
    """, unsafe_allow_html=True)

# ── 第 2 行：传感器 (左) | 执行器 (右) ──
r2_c1, r2_c2 = st.columns(2)

with r2_c1:
    # 传感器 3x3 阵列
    metrics_html = ""
    sensors = [
        ("空气温度", data.get('temp'), "°C"), ("空气湿度", data.get('humidity'), "%"), ("甲醛 (CH2O)", data.get('ch2o'), "μg"),
        ("二氧化碳", data.get('co2'), "ppm"), ("电导率 (EC)", data.get('ec'), "μS/cm"), ("酸碱度 (pH)", data.get('ph'), ""),
        ("PM 2.5", data.get('pm25'), "μg/m³"), ("PM 10", data.get('pm10'), "μg/m³"), ("挥发物 (TVOC)", data.get('tvoc'), "ppb")
    ]
    for k, v, u in sensors:
        metrics_html += f'<div class="m-box"><div class="m-title">{k}</div><div class="m-val">{v if v is not None else "--"}<span class="m-unit">{u}</span></div></div>'
    
    st.markdown(f"""
    <div class="p-card" style="height: 100%;">
        <div class="p-header">📊 传感器阵列</div>
        <div class="p-body"><div class="sensor-grid">{metrics_html}</div></div>
    </div>
    """, unsafe_allow_html=True)

with r2_c2:
    # 执行器方阵格式
    def get_stat(keyword):
        for l in logs[:8]:
            if l['type'] == '执行' and keyword in l['content']:
                return "act-on" if "ON" in l['content'] else ""
        return ""

    acts_html = f"""
    <div class="act-grid">
        <div class="act-cell {get_stat('补光')}"><div class="act-dot"></div><span>补光灯</span></div>
        <div class="act-cell {get_stat('打氧')}"><div class="act-dot"></div><span>打氧水泵</span></div>
        <div class="act-cell {get_stat('养液泵')}"><div class="act-dot"></div><span>营养液泵</span></div>
        <div class="act-cell {get_stat('进风')}"><div class="act-dot"></div><span>进气风扇</span></div>
        <div class="act-cell {get_stat('出风')}"><div class="act-dot"></div><span>排气风扇</span></div>
    </div>
    """
    st.markdown(f"""
    <div style="height: 100%; display: flex; flex-direction: column; gap: 20px;">
        <div class="p-card" style="height: auto; margin-bottom: 0;">
            <div class="p-header">⚙️ 执行器状态</div>
            <div class="p-body">{acts_html}</div>
        </div>
        <div class="p-card" style="height: auto; margin-bottom: 0; margin-top: auto; padding: 12px 15px; display: flex; align-items: center; justify-content: flex-end; background-color: #8b5a2b; border-color: #4a2e19;">
            <a href="https://github.com/ZtongCai/houji" target="_blank" style="color: #f4e4bc; font-weight: bold; text-decoration: none; font-size: 22px; display: inline-flex; align-items: center; gap: 10px;">
                <svg height="26" width="26" viewBox="0 0 16 16" fill="#f4e4bc"><path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>
                Github: ZtongCai/houji
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 自动刷新
time.sleep(30)
st.rerun()
