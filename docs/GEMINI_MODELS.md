# 后稷项目 Gemini API 可用模型清单
# 由 `curl .../v1beta/models?key=...` 于 2026-04-06 查询获得

## 文字/多模态生成（本项目主力）

| 模型名 | 推荐用途 |
|---|---|
| `gemini-2.5-flash` | ⭐ 最新最快，日常决策首选 |
| `gemini-2.0-flash` | 稳定版 Flash，当前 config 默认 |
| `gemini-2.0-flash-lite` | 极速轻量版，Token 消耗最少 |
| `gemini-2.5-pro` | 最强推理，疑难分析备用 |
| `gemini-3-flash-preview` | 下一代 Flash 预览版（待正式发布） |
| `gemini-3-pro-preview` | 下一代 Pro 预览版（待正式发布） |

## 当前 config.py 配置

```python
GEMINI_FLASH_MODEL = "gemini-2.0-flash"   # 日常决策
GEMINI_PRO_MODEL   = "gemini-2.5-pro"     # 疑难分析
```

## 嵌入模型（Phase 2 LightRAG 向量检索用）

| 模型名 | 用途 |
|---|---|
| `gemini-embedding-001` | 文本向量化，接入 LightRAG |
| `gemini-embedding-2-preview` | 新一代嵌入预览版 |

## 图像生成（本项目暂不使用）
- `imagen-4.0-generate-001`
- `imagen-4.0-ultra-generate-001`

## 视频生成（本项目暂不使用）
- `veo-3.0-generate-001`
- `veo-3.0-fast-generate-001`

## 注意事项
- `gemini-1.5-flash` / `gemini-1.5-pro` **此 Key 不可用**（旧版 API）
- `gemma-*` 系列是开源小模型，可本地部署但不适合多模态决策
- Preview / Experimental 模型随时可能下线，生产环境慎用
