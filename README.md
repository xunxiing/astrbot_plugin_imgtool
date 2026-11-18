# astrbot_plugin_imgtool

一款 AstrBot 插件 —— 在插件配置面板暴露 `provider/base_url/model/api_key`，`provider` 使用下拉列表（siliconflow/openrouter/modelscope/custom）；暴露 LLM 函数工具 `imagine`，可被函数调用（function-calling）自动触发；也可手动命令 `/img` 使用。

已适配提供商：

- SiliconFlow：OpenAI 风格 `/v1/images/generations`
- OpenRouter：OpenAI 风格 `/v1/images/generations`
- ModelScope（魔搭社区）：异步提交 `/v1/images/generations` + 轮询 `/v1/tasks/{task_id}`，支持参考图字段 `ref_image.url`

适配层解耦，后续按需扩展更多 Provider。支持在函数调用里传 `model=edit` 作为别名（将按配置项 `edit_model` 映射到实际模型，例如 `Qwen/Qwen-Image-Edit`）。参考图既可以 data URL，也可直接用 http(s) 直链；直链会在本地尝试抓取，失败则回退为把 URL 直接交给服务端拉取。为避免 Provider 返回的临时 URL 过期，插件会主动把图片下载保存到 `AstrBot/data/<save_dir>` 下。

## 安装

将本目录放到 `AstrBot/data/plugins/astrbot_plugin_imgtool`，然后在 WebUI 插件管理中启用并配置。

## 使用

- 指令：`/img 一个小岛，海鸥与灯塔……`
- LLM 工具：在对话中触发函数调用 `imagine`（参数同 README 顶部说明）。当以工具方式调用成功后，将向 Bot 返回包含 base64 图片的结果（`{"images": ["data:image/png;base64,...", ...]}`）。

### 使用 ModelScope（魔搭）

- 配置 `provider=modelscope`
- 可留空 `base_url`，适配器默认使用 `https://api-inference.modelscope.cn/v1`
- 会以异步方式提交任务（请求头 `X-ModelScope-Async-Mode: true`），再轮询 `/v1/tasks/{task_id}` 获取结果
- 参考图通过 `ref_image.url` 传入（若模型支持），建议使用公网可访问 URL；也支持 data URL

## 自定义 Provider

- **先把配置顶部的 `provider` 下拉框切成 `custom`**（这一步最容易漏；只填下面的「自定义 OpenAI Images 接口配置」而不切 provider 是不会生效的）。
- 然后在「自定义 OpenAI Images 接口配置」里填 `base_url`、`api_key`、`model`：
  - `base_url` 可以填完整端点 `https://your.host/v1/images/generations`，也可以只填 `https://your.host/v1` 或 `https://your.host`，插件会自动补齐 `/v1/images/generations`；
  - 只要对方遵循 OpenAI 风格的 `/images/generations` JSON 即可（字段见 `adapters/custom_http.py`）。
- 也可以在聊天里用 `/imgprovider custom` 切换，`/imgprovider` 不带参数会列出各 provider 是否已填 api_key。
- 若配置里的 `provider` 仍是默认值、而只有一个分组填了 api_key，插件会自动使用那个分组，并打印一条 warning 提示。

