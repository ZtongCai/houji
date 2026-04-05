"""
LightRAG 长期记忆模块
负责：
  1. 索引《生菜水培手册》（静态知识）
  2. 每日追加 AI 生长观察日记（动态记忆）
  3. 在 AI 决策前提供相关上下文检索
"""
import logging
from config import RAG_STORE_DIR

log = logging.getLogger("houji.rag")

# TODO: Phase2 —— 安装并导入 lightrag
# from lightrag import LightRAG, QueryParam
# from lightrag.llm.openai import openai_embed
# rag = LightRAG(working_dir=str(RAG_STORE_DIR), ...)


def insert_document(text: str, doc_id: str = ""):
    """向 RAG 知识库插入一段文档"""
    log.info(f"[RAG] 插入文档: {doc_id[:30]}...  (TODO: 接入 LightRAG)")


def insert_diary(entry: str):
    """追加一条 AI 生长日记到 RAG 记忆"""
    log.info(f"[RAG] 记录日记: {entry[:50]}...  (TODO: 接入 LightRAG)")


def query(question: str) -> str:
    """检索与问题最相关的历史上下文"""
    log.info(f"[RAG] 查询: {question}  (TODO: 接入 LightRAG)")
    return ""
