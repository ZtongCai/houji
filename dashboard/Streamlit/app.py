"""
后稷 Pro 看板 v3.0 (Legacy Pixel Edition)
终极修复版：放弃碎片化 st 组件，改用全容器 HTML 渲染，确保样式和日志绝不泄露源码。
"""
import time
import json
import sqlite3
import base64
from html import escape
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ── 配置 ──────────────────
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "brain"))
try:
    from config import (
        CROP_NAME,
        CURRENT_GROWTH_STAGE,
        DATA_DIR as CONFIG_DATA_DIR,
        EC_TARGET_MAX,
        EC_TARGET_MIN,
        GROWTH_STAGE,
        INSTANCE_ID,
        PLANTING_BATCH,
        PLANTING_START_DATE,
        RUN_MODE,
        SENSOR_INTERVAL,
        EC_TARGETS, CROP_PROFILE_NAME, GROWTH_STAGE_MODE, GROWTH_STATE_PATH,
    )
    from vision import load_stage
    stage_state = load_stage(GROWTH_STATE_PATH, PLANTING_BATCH, CROP_PROFILE_NAME, GROWTH_STAGE, EC_TARGETS)
    active_stage = GROWTH_STAGE if GROWTH_STAGE_MODE == "manual" else stage_state["effective_stage"]
    CURRENT_GROWTH_STAGE = EC_TARGETS[active_stage]
    EC_TARGET_MIN, EC_TARGET_MAX = CURRENT_GROWTH_STAGE["min"], CURRENT_GROWTH_STAGE["max"]
    start_dt = datetime.strptime(PLANTING_START_DATE, "%Y-%m-%d")
    current_day = max(1, (datetime.now() - start_dt).days + 1)
    batch_info = f"实例: {INSTANCE_ID} | 批次: {PLANTING_BATCH} | Day {current_day}"
except Exception as exc:
    CROP_NAME = "未知作物"
    CURRENT_GROWTH_STAGE = {"label": "未知阶段"}
    EC_TARGET_MIN = 0
    EC_TARGET_MAX = 0
    GROWTH_STAGE = "unknown"
    INSTANCE_ID = "unknown"
    RUN_MODE = "unknown"
    SENSOR_INTERVAL = 10
    CONFIG_DATA_DIR = PROJECT_ROOT / "brain" / "data"
    batch_info = f"配置加载失败: {exc}"

DATA_DIR = Path(CONFIG_DATA_DIR)
DB_PATH      = DATA_DIR / "houji.db"
THOUGHT_LOG  = DATA_DIR / "thought.log"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

st.set_page_config(page_title=f"HOUJI · {CROP_NAME}", page_icon="\U0001F33F", layout="wide", initial_sidebar_state="collapsed")

# ── 核心工具 ──────────────────
def img_to_b64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return ""

def load_farm_data():
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1").fetchone()
        if not row: return {}
        cols = [d[0] for d in conn.execute("SELECT * FROM sensor_readings LIMIT 1").description]
        return dict(zip(cols, row))
    except: return {}
    finally: conn.close()

def load_history_data(limit=None):
    if not DB_PATH.exists():
        return pd.DataFrame()
    if limit is None:
        limit = max(100, int(3 * 24 * 3600 / max(SENSOR_INTERVAL, 1)))
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        # 取过去 3 天 (1分钟1次大概4320次)
        df = pd.read_sql_query("SELECT timestamp, temp, ec FROM sensor_readings ORDER BY timestamp DESC LIMIT ?", conn, params=(limit,))
        df = df.sort_values("timestamp")
        # 修复 1970 Bug: SQLite 存的是秒级浮点数时间戳，必须指定 unit='s'，并加上东八区时差
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s') + pd.Timedelta(hours=8)
        df.set_index("timestamp", inplace=True)
        # 按15分钟精细重采样取平均值，dropna 去除没有数据的时刻
        df_hourly = df.resample('15min').mean().dropna().reset_index()
        return df_hourly
    except:
        return pd.DataFrame()
    finally:
        conn.close()

def load_daily_data():
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        df = pd.read_sql_query("SELECT timestamp, temp, humidity, co2, ec FROM sensor_readings ORDER BY timestamp ASC", conn)
        if df.empty: return pd.DataFrame()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s') + pd.Timedelta(hours=8)
        df.set_index("timestamp", inplace=True)
        # 按天重采样取平均
        df_daily = df.resample('1D').mean().dropna()
        # 截取小数点并把列名换成中文方便显示
        df_daily = df_daily.rename(columns={'temp': '温度(°C)', 'humidity': '湿度(%)', 'co2': 'CO2(ppm)', 'ec': '电导率'})
        # 保留 datetime index，不再转成 string，以便图表引擎正确解析时间
        df_daily.index.name = 'timestamp'
        return df_daily
    except:
        return pd.DataFrame()
    finally:
        conn.close()

def _load_jsonl_records(path):
    records = []
    try:
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(records) >= 20:
                break
    except (OSError, UnicodeError):
        pass
    return records

def _load_legacy_records(path):
    records = []
    try:
        blocks = path.read_text(encoding="utf-8").rsplit("=" * 60, 20)[-20:]
    except (OSError, UnicodeError):
        return records

    labels = {
        "???: ": "sensor_data",
        "??: ": "image_path",
        "??: ": "model",
        "??: ": "thought",
        "??: ": "actions",
        "??: ": "results",
    }
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines or not lines[0].startswith("["):
            continue
        record = {"ts": lines[0].strip("[]")}
        current_key = None
        for line in lines[1:]:
            for label, key in labels.items():
                if line.startswith(label):
                    record[key] = line[len(label):]
                    current_key = key
                    break
            else:
                if current_key == "thought":
                    record["thought"] += "\n" + line
        try:
            for key in ("sensor_data", "actions", "results"):
                default = "{}" if key == "sensor_data" else "[]"
                record[key] = json.loads(record.get(key, default))
        except json.JSONDecodeError:
            continue
        records.append(record)
    return records


def load_farm_logs():
    records = []
    for legacy_log in sorted(DATA_DIR.glob("thought.log.legacy-*")):
        records.extend(_load_legacy_records(legacy_log))
    if THOUGHT_LOG.exists():
        records.extend(_load_jsonl_records(THOUGHT_LOG))
    records = sorted(records, key=lambda record: str(record.get("ts", "")), reverse=True)[:20]

    items = []
    names = {1: "养液泵", 2: "进风", 3: "出风", 7: "打氧", 8: "补光"}
    for record in records:
        ts = record.get("ts", "未知时间")
        thought = escape(str(record.get("thought", ""))).replace("\n", "<br>")
        image_input = record.get("image_input") or {}
        growth = record.get("growth") or {}
        if image_input:
            vision_status = "图片请求成功" if image_input.get("request_succeeded") else "视觉不可用"
            detail = (
                f"{vision_status} | 拍摄：{image_input.get('captured_at', '无')} | "
                f"照片：{Path(image_input.get('path', '')).name} | "
                f"识别阶段：{growth.get('stage', 'unknown')} | 生效阶段：{record.get('effective_stage', '未知')} | "
                f"EC目标：{record.get('ec_target', {}).get('min', '?')}–{record.get('ec_target', {}).get('max', '?')} μS/cm | "
                f"观察：{growth.get('condition', '')} | 证据：{'；'.join(growth.get('evidence', []))} | "
                f"不确定项：{'；'.join(growth.get('uncertainty', []))} {image_input.get('error', '')}"
            )
            thought = escape(detail) + "<br>" + thought
        model_name = record.get("model", "未知")
        items.append({"ts": ts, "type": f"分析 | {model_name}", "content": thought, "color": "#2e5d9b"})
        actions = record.get("actions") or []
        if not actions:
            continue
        parts = []
        for action in actions:
            relay_id = action.get("relay_id", 0)
            name = names.get(relay_id, f"R{relay_id}")
            state = "ON" if action.get("state") else "OFF"
            parts.append(f"{name} {state}")
        action_type = "执行指令" if RUN_MODE == "control" else "AI 建议（已拦截）"
        items.append({"ts": ts, "type": action_type, "content": f"动作: {' | '.join(parts)}", "color": "#348e3e"})
    return items[:40]

# ── 渲染核心 ──────────────────

# 准备数据
data = load_farm_data()
logs = load_farm_logs()
snaps = sorted(SNAPSHOT_DIR.glob("*.jpg"))
img_b64 = img_to_b64(snaps[-1]) if snaps else ""

latest_ts = data.get("timestamp")
if isinstance(latest_ts, (int, float)):
    data_age_seconds = max(0, time.time() - latest_ts)
else:
    data_age_seconds = None
is_fresh = data_age_seconds is not None and data_age_seconds <= max(60, SENSOR_INTERVAL * 3)
mode_label = "控制模式" if RUN_MODE == "control" else "观察模式（继电器已禁用）"
data_label = "数据实时" if is_fresh else "数据缺失或已过期"
status_color = "#2e7d32" if is_fresh else "#b71c1c"

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
        <div style="font-size:38px;">🌱 后稷 HOUJI · 水培{CROP_NAME}</div>
        <div style="font-size:22px;">
            {batch_info} | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 模型: Qwen 3.7 Plus
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:{status_color}; color:white; padding:10px 18px; margin:-12px 0 20px 0;
            font-family:monospace; border:3px solid #4a2e19;">
    {mode_label} ｜ {data_label} ｜ 阶段：{CURRENT_GROWTH_STAGE['label']}
    ｜ EC目标：{EC_TARGET_MIN:.0f}–{EC_TARGET_MAX:.0f} μS/cm
</div>
""", unsafe_allow_html=True)


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
    <div class="p-card" style="height: auto; margin-bottom: 20px;">
        <div class="p-header">📊 传感器阵列</div>
        <div class="p-body"><div class="sensor-grid">{metrics_html}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ==== 历史趋势图 ====
    # 用 p-card 做标题壳，图表自身背景色设为 #fcf5e5 完美融入
    st.markdown("""
    <div class="p-card" style="height: auto; padding-bottom: 0; margin-bottom: 0;">
        <div class="p-header">📈 核心参数趋势 (近3天 · 15分钟精细聚合)</div>
    </div>
    """, unsafe_allow_html=True)

    df_history = load_history_data()
    if not df_history.empty:
        import altair as alt

        base = alt.Chart(df_history).encode(
            x=alt.X('timestamp:T', title='时间',
                    axis=alt.Axis(format='%m-%d %H:%M', labelColor='#4a2e19',
                                  titleColor='#4a2e19', grid=False, labelAngle=-45))
        )

        line_temp = base.mark_line(color='#d63031', strokeWidth=3,
                                   point=alt.OverlayMarkDef(color='#d63031', size=50)).encode(
            y=alt.Y('temp:Q', title='温度 (°C)', scale=alt.Scale(zero=False),
                    axis=alt.Axis(titleColor='#d63031', labelColor='#d63031',
                                  gridColor='rgba(0,0,0,0.08)'))
        )

        line_ec = base.mark_line(color='#0984e3', strokeWidth=3,
                                 point=alt.OverlayMarkDef(color='#0984e3', size=50)).encode(
            y=alt.Y('ec:Q', title='电导率 (μS/cm)', scale=alt.Scale(zero=False),
                    axis=alt.Axis(titleColor='#0984e3', labelColor='#0984e3', grid=False))
        )

        chart = alt.layer(line_temp, line_ec).resolve_scale(y='independent').properties(
            height=330,
            padding={'top': 18, 'left': 8, 'right': 8, 'bottom': 8}
        )
        # 关键：背景色与卡片体的黄纸色一致，视觉上无缝拼合
        chart = chart.configure(background='#fcf5e5').configure_view(strokeWidth=0)

        st.altair_chart(chart, use_container_width=True)
    else:
        st.markdown("<div style='color:#4a2e19; padding: 20px;'>暂无足够的历史数据...</div>", unsafe_allow_html=True)

with r2_c2:
    # 执行器方阵格式 (抛弃脆弱的日志解析，采用工业级闭环电平提取)
    def get_stat(rid):
        if RUN_MODE != "control":
            return "", "未控制"
        try:
            with open(DATA_DIR / "hardware_status.json", "r", encoding="utf-8") as f:
                st_data = json.load(f)
            if not st_data.get("connected"):
                return "", "未知"
            relays = st_data.get("relays", {})
            is_on = relays.get(str(rid)) == 1 or relays.get(rid) == 1
            return ("act-on", "ON") if is_on else ("", "OFF")
        except Exception:
            return "", "未知"

    def actuator_cell(rid, name):
        css_class, status = get_stat(rid)
        return (
            f'<div class="act-cell {css_class}"><div class="act-dot"></div>'
            f'<span>{name}</span><small>{status}</small></div>'
        )

    acts_html = '<div class="act-grid">' + ''.join([
        actuator_cell(8, "补光灯"),
        actuator_cell(7, "打氧水泵"),
        actuator_cell(1, "营养液泵"),
        actuator_cell(2, "进气风扇"),
        actuator_cell(3, "排气风扇"),
    ]) + '</div>'
    st.markdown(f"""
    <div class="p-card" style="height: auto; margin-bottom: 20px;">
        <div class="p-header">⚙️ 执行器状态</div>
        <div class="p-body">{acts_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # ==== 宏观日均值走势图 ====
    st.markdown("""
    <div class="p-card" style="height: auto; padding-bottom: 0; margin-bottom: 0;">
        <div class="p-header" style="margin-bottom: -8px;">📅 全周期宏观日志 (日均走势分析)</div>
    </div>
    """, unsafe_allow_html=True)

    df_daily = load_daily_data()
    if not df_daily.empty:
        plot_df = df_daily.reset_index()
        import altair as alt

        # ── 关键 CSS：让图表容器背景色与图表本身相同，缝隙彻底不可见 ──
        st.markdown("""
        <style>
        /* 让所有 VegaLite 图表的外层容器背景也变成黄纸色，从视觉上消除任何间隙 */
        .element-container:has(.stVegaLiteChart) {
            background-color: #fcf5e5 !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        .stMarkdown + .element-container { margin-top: -10px !important; }
        </style>
        """, unsafe_allow_html=True)

        metrics = [
            ('温度(°C)',  '温度 (°C)',  '#d63031', False),
            ('湿度(%)',   '湿度 (%)',   '#0984e3', False),
            ('CO2(ppm)', 'CO2 (ppm)', '#00b894', False),
            ('电导率',    'EC (μS/cm)','#6c5ce7', True),
        ]

        for y_col, label, color, show_x in metrics:
            x_ax = (
                alt.Axis(format='%m-%d', labelAngle=-30, labelColor='#4a2e19',
                         grid=False, title=None, tickCount=7)
                if show_x else
                alt.Axis(labels=False, ticks=False, grid=False, title=None)
            )
            base = alt.Chart(plot_df).properties(height=78)

            area = base.mark_area(color=color, opacity=0.3, interpolate='monotone').encode(
                x=alt.X('timestamp:T', axis=x_ax),
                y=alt.Y(f'{y_col}:Q', scale=alt.Scale(zero=False),
                        axis=alt.Axis(title=label, titleColor=color, titleFontSize=11,
                                      labelColor='#4a2e19', tickCount=3,
                                      grid=True, gridColor='rgba(0,0,0,0.07)',
                                      labelFontSize=10))
            )
            line = base.mark_line(color=color, strokeWidth=2, interpolate='monotone').encode(
                x=alt.X('timestamp:T', axis=x_ax),
                y=alt.Y(f'{y_col}:Q')
            )
            c = (
                alt.layer(area, line)
                .configure(background='#fcf5e5')
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(c, use_container_width=True)
    else:
        st.markdown("<div style='color:#4a2e19; padding:20px;'>暂无数据</div>", unsafe_allow_html=True)




# ── 全宽底部 GitHub 条（在所有列之外独立渲染）──
st.markdown("""
<div style="background-color: #8b5a2b; border: 4px solid #4a2e19; padding: 12px 25px;
            display: flex; align-items: center; justify-content: flex-end;
            font-family: 'VT323', monospace; margin-top: 4px;">
    <a href="https://github.com/ZtongCai/houji" target="_blank"
       style="color: #f4e4bc; font-weight: bold; text-decoration: none;
              font-size: 24px; display: inline-flex; align-items: center; gap: 12px;">
        <svg height="28" width="28" viewBox="0 0 16 16" fill="#f4e4bc"><path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>
        Github: ZtongCai/houji
    </a>
</div>
""", unsafe_allow_html=True)

# 自动刷新
time.sleep(30)
st.rerun()
