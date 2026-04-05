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

# ── 配置（根据实际 Samba 挂载路径修改）──────────────────
DATA_DIR     = Path("Z:/data")          # Samba 映射路径
DB_PATH      = DATA_DIR / "houji.db"
THOUGHT_LOG  = DATA_DIR / "thought.log"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

st.set_page_config(page_title="后稷 · 水培生菜 AI 看板", layout="wide")
st.title("🌱 后稷 · 水培生菜 AI 农场")

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
            "SELECT temp, humidity, ph, ec, timestamp FROM sensor_readings ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            temp, humidity, ph, ec, ts = row
            c1, c2 = st.columns(2)
            c1.metric("🌡 温度", f"{temp} °C" if temp else "N/A")
            c2.metric("💧 湿度", f"{humidity} %" if humidity else "N/A")
            c3, c4 = st.columns(2)
            c3.metric("⚗️ pH",  f"{ph}" if ph else "N/A")
            c4.metric("⚡ EC",  f"{ec} mS/cm" if ec else "N/A")
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
        st.text_area("", "\n".join(lines[-50:]), height=600)
    else:
        st.info("暂无日志（等待 Pi 5 生成...）")
