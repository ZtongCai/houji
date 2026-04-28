import sqlite3
import os
import sys

db_path = r"z:/brain/data/houji.db"

if os.path.exists(db_path):
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM sensor_readings")
            conn.commit()
            conn.execute("VACUUM")
        print("✅ 数据库表 sensor_readings 已成功清空。")
    except Exception as e:
        print(f"❌ 清理数据库时发生错误: {e}")
        sys.exit(1)
else:
    print("⚠️ 数据库文件未找到，不需要清理。")
