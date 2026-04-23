"""
后稷直播看板（Windows 端 Streamlit）
从 Samba 共享盘读取数据，渲染三栏科技感看板：
  左栏：生菜实况图
  中栏：传感器仪表盘
  右栏：AI 思考日志
"""
import time
import sqlite3
import streamlit as st
from pathlib import Path

# ── 配置（自适应数据路径）──────────────────
# 优先寻找包含 houji.db 的目录
def find_data_dir():
    candidates = [
        Path("Z:/"),                # Samba 映射为 Z: 盘
        Path("Z:/brain/data"),      # Samba 映射为根目录
        Path(__file__).parent.parent.parent / "brain" / "data", # 本地相对路径
        Path("./brain/data"),       # 当前目录下
    ]
    for d in candidates:
        if d.exists() and (d / "houji.db").exists():
            return d
    return candidates[0] # 默认回退到 Z:

DATA_DIR = find_data_dir()
DB_PATH      = DATA_DIR / "houji.db"
THOUGHT_LOG  = DATA_DIR / "thought.log"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

st.set_page_config(page_title="后稷 · 水培生菜 AI 看板", layout="wide")
st.title("🌱 后稷 · 水培生菜 AI 农场")

# 调试信息（仅在没找到数据库时显示，或放在侧边栏）
with st.sidebar:
    st.write(f"📂 **当前数据目录**: `{DATA_DIR.absolute()}`")
    if not DB_PATH.exists():
        st.error("❌ 未在上述目录找到 `houji.db`，请检查 Z 盘挂载或路径！")

# ── 自动刷新（60 秒）────────────────────────────────────
st.markdown(
    '<meta http-equiv="refresh" content="60">',
    unsafe_allow_html=True,
)

col_cam, col_sensor, col_log = st.columns([1, 1, 1])

# ── 左栏：生菜实况 ───────────────────────────────────────
with col_cam:
    st.subheader("📷 生菜实况")
    snapshots = sorted(SNAPSHOT_DIR.glob("*.jpg")) if SNAPSHOT_DIR.exists() else []
    if snapshots:
        st.image(str(snapshots[-1]), use_container_width=True)
        st.caption(f"最新快照：{snapshots[-1].name}")
    else:
        st.info("暂无快照（等待 Pi 5 上传...）")

# ── 中栏：传感器仪表盘 ────────────────────────────────────
with col_sensor:
    st.subheader("📊 传感器数据")
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            """SELECT temp, humidity, co2, ch2o, tvoc, pm25, pm10, ec, ph, timestamp
               FROM sensor_readings ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()
        conn.close()
        if row:
            temp, humi, co2, ch2o, tvoc, pm25, pm10, ec, ph, ts = row
            c1, c2 = st.columns(2)
            c1.metric("🌡 温度",  f"{temp} °C"    if temp else "N/A")
            c2.metric("💧 湿度",  f"{humi} %"     if humi else "N/A")
            c3, c4 = st.columns(2)
            c3.metric("🌬 CO₂",  f"{co2} ppm"    if co2  else "N/A")
            c4.metric("🧪 TVOC", f"{tvoc} ppb"   if tvoc else "N/A")
            c5, c6 = st.columns(2)
            c5.metric("⚗️ pH",   f"{ph}"          if ph   else "N/A")
            c6.metric("⚡ EC",   f"{ec} mS/cm"   if ec   else "N/A")
            c7, c8 = st.columns(2)
            c7.metric("🌫 PM2.5", f"{pm25} μg/m³" if pm25 else "N/A")
            c8.metric("🌫 PM10",  f"{pm10} μg/m³" if pm10 else "N/A")
            st.caption(f"最后更新：{time.strftime('%H:%M:%S', time.localtime(ts))}")
        else:
            st.info("数据库为空")
    else:
        st.info("数据库未找到（等待 Samba 挂载...）")

# ── 右栏：AI 思考日志 ─────────────────────────────────────
with col_log:
    st.subheader("🤖 AI 思考日志")
    if THOUGHT_LOG.exists():
        lines = THOUGHT_LOG.read_text(encoding="utf-8").splitlines()
        st.text_area("", "\n".join(lines[-60:]), height=600)
    else:
        st.info("暂无日志（等待 Pi 5 生成...）")
