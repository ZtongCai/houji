"""
测试 AI 大模型决策中枢（真实调用 Gemini，不 Mock）
运行前请确保：
  1. 已安装依赖: pip install langgraph langchain-google-genai pydantic
  2. 已设置环境变量: export GEMINI_API_KEY=AIza...
     （或者 config.py 中已内嵌 API Key）
  3. Pico 已连上 USB，spine/main.py 已运行（用于测试继电器执行）
     若没有 Pico，run_cycle() 内的串口会失败但不 crash，程序正常运行
"""
import sys
from pathlib import Path

# 将 brain 目录加入 sys.path，以便导入核心模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'brain'))

from ai_engine import run_cycle

if __name__ == "__main__":
    print("--- [后稷项目] LangGraph AI 决策中枢实机测试 ---")
    print("正在执行一次完整决策周期：感知 → Gemini 决策 → 继电器执行 → 日志写入\n")
    
    run_cycle()
    
    print("\n✅ 决策周期执行完成！请检查以下结果：")
    print("  1. brain/data/thought.log 是否有新增的决策记录")
    print("  2. 继电器是否按照 AI 的指令发出了哒哒声")
