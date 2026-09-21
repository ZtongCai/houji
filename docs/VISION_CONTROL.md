# 图片与自动生长阶段控制

每次 AI 决策前拍摄新照片，将 JPEG（最长边 1280、质量 85）的 Base64 图片与传感器、最近 10 条历史和最近设备状态发送给 qwen3.7-plus。照片须为本轮拍摄且不超过 300 秒；失败时明确记录视觉不可用，不替换成历史照片。

模型返回 `growth`：图片可用性、阶段、视觉证据、生长状态、不确定项。`seedling` / `growth` / `mature` 对应原有配置；`flowering` 和 `fruiting` 映射到 `mature`。不增加或改写 EC 范围、稀释比例和泵时长。

`GROWTH_STAGE_MODE=auto`：连续两张不同图片的有效判断映射到同一阶段后，更新本轮生效阶段。缺图、API 失败、unknown 或无证据中断连续计数，保留最近确认阶段。`GROWTH_STAGE` 是首次启动兜底值；`manual` 模式下它是人工覆盖值，但模型仍观察图片。

状态原子写入 `brain/data/growth_state.json`，绑定种植批次与作物配置。更换批次后重新确认。模型只选择阶段，程序按该阶段查 EC 表，执行层使用同一阶段下限校验加液。现有泵 10 秒限制、观察模式及 Pico 定时关闭保持不变。视觉判断及连续确认不是农艺准确性的保证。

`thought.log` 记录 `image_input`（文件、时间、发送内容 SHA256、大小、API 成功状态）、`growth`、`effective_stage`、`ec_target` 和请求 ID。不保存 Base64。看板显示识别与生效阶段、图像证据和动态 EC 目标。

离线回归：`PYTHONDONTWRITEBYTECODE=1 brain/venv/bin/python test/test_vision.py`。测试使用模拟 API 和继电器，验证图片编码、过期、阶段连续确认、批次隔离、失败降级与动态 EC 门控。
