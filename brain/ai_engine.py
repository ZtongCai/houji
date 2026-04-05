"""
Gemini AI 决策引擎
负责：
  1. 将传感器数值 + 快照 + 系统提示词送入 Gemini
  2. 解析 AI 返回的动作指令（JSON）
  3. 将思考过程写入 thought.log
"""
import json
import logging
from pathlib import Path
from config import GEMINI_API_KEY, GEMINI_FLASH_MODEL, GEMINI_PRO_MODEL, THOUGHT_LOG_PATH

log = logging.getLogger("houji.ai")

# TODO: Phase2 —— 安装并导入 google-genai
# import google.generativeai as genai
# genai.configure(api_key=GEMINI_API_KEY)

# 系统提示词
SYSTEM_PROMPT = """
你是"后稷"，一个专业的水培生菜 AI 农场主。
你的目标是让两棵生菜健康成长。
请根据传感器数据和摄像头图像，以 JSON 格式给出操作指令：
{
  "thought": "你的分析思路",
  "actions": [
    {"device": "light", "state": 1},
    {"device": "fan",   "state": 0},
    {"device": "pump",  "state": 0}
  ]
}
"""


def decide(sensor_data: dict, image_path: Path | None = None, use_pro: bool = False) -> dict | None:
    """
    调用 Gemini 进行决策
    :param sensor_data: 传感器读数字典
    :param image_path:  最新快照路径（可选）
    :param use_pro:     True 则切换至 Pro 模型
    :return: 解析后的指令字典，失败返回 None
    """
    model_name = GEMINI_PRO_MODEL if use_pro else GEMINI_FLASH_MODEL
    log.info(f"[AI] 使用模型: {model_name}")

    # TODO: Phase2 —— 构造 contents 并调用 Gemini API
    log.info(f"[AI] 传感器数据: {sensor_data}  (TODO: 接入 Gemini)")
    return None


def log_thought(thought: str):
    """将 AI 思考内容追加写入 thought.log"""
    with open(THOUGHT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(thought + "\n")
