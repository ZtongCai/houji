import sys
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'brain'))

from config import SNAPSHOT_DIR
from ai_engine import _graph

# 临时：把测试快照复制进 snapshots/ 供 AI 使用
TEST_SNAP = Path(__file__).resolve().parent / "test_snapshot.jpg"
if TEST_SNAP.exists():
    dest = SNAPSHOT_DIR / f"{int(time.time())}.jpg"
    shutil.copy(TEST_SNAP, dest)
    print(f"[测试] 快照已就位: {dest}\n")
else:
    print("[测试] 无测试快照，AI 将在无图模式下决策\n")

if __name__ == "__main__":
    print("=" * 60)
    print("    后稷 AI 决策中枢 · 实机测试（流式输出）")
    print("=" * 60 + "\n")

    init_state = {
        "sensor_data": {}, "image_path": None,
        "thought": "", "actions": [], "results": [],
    }

    # 流式逐节点输出
    for event in _graph.stream(init_state, stream_mode="updates"):
        for node, output in event.items():
            if node == "sense":
                print("📡 [感知完成]")
                print(f"   传感器: {output.get('sensor_data', {})}")
                print(f"   快照  : {output.get('image_path')}\n")

            elif node == "decide":
                print("🧠 [Gemini 决策完成]")
                print(f"\n{output.get('thought', '（无思考内容）')}\n")
                print(f"   动作列表: {output.get('actions', [])}\n")

            elif node == "execute":
                print("⚙️  [执行完成]")
                for r in output.get('results', []):
                    a = r['action']
                    d = a.get('duration_seconds', 0)
                    dur_str = f"（定时 {d}s）" if d > 0 else "（持续）"
                    print(f"   继电器{a['relay_id']} {'ON' if a['state'] else 'OFF'} {dur_str} → {r['resp']}")
                print()

            elif node == "log":
                print("📝 [已写入 thought.log]\n")

    print("=" * 60)
    print("✅ 决策周期完成！")

