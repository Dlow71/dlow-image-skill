---
name: dlow-image
description: 使用 DLow 的 gpt-image-2.6 模型生成图片或动态 GIF。用户要求用 DLow、gpt-image-2.6 画图或生成 GIF 时使用；缺少 API 密钥时先询问用户。
---

# DLow 图片与 GIF

固定接口：`https://www.dlowapi.me/v1/images/generations`，模型：`gpt-image-2.6`。

## 使用流程

1. 使用当前进程的 `DLOW_API_KEY`，或本轮用户已提供的密钥。两者都没有时，直接询问：“请提供你的 DLow API 密钥（用于 https://www.dlowapi.me/v1），我会用它生成图片／GIF。” 等用户回复后再请求，不要猜测或使用示例密钥。
2. 根据用户内容编写提示词。普通图片默认 PNG；动画使用 GIF，并在提示词中明确动作、循环方式和背景。默认生成 1 份。
3. 用 Python 3 运行本 skill 的 `scripts/generate.py`，通过单次子进程环境变量 `DLOW_API_KEY` 传入密钥。脚本只依赖标准库，不需要安装包。执行前把占位路径替换为实际路径：

   ```bash
   python3 <skill目录>/scripts/generate.py --prompt '一颗蓝色小球上下弹跳，白色背景，无缝循环的动态 GIF，不要精灵图或静态分镜' --format gif --out <输出目录>/ball.gif
   ```

   普通图片使用 `--format png`。可选 `--size 1024x1024`、`--quality auto`、`--timeout 240`。AI 从用户消息取得密钥后，用执行工具的子进程环境注入，或用安全引用的临时环境赋值。不要把密钥写进 skill、脚本、`.env`、交付文件或示例，不要回显密钥。提示词含特殊字符时使用参数数组或正确 shell 引用。
4. 脚本输出实际路径、格式、PNG/GIF 尺寸及 GIF 帧数。GIF 只有一帧时，告知用户它是静态 GIF。服务可能忽略请求尺寸和帧数，按实际结果描述。
5. 展示生成文件；支持本地媒体的客户端使用绝对路径 Markdown 图片，例如 `![生成结果](/绝对路径/ball.gif)`，否则提供文件附件或路径。

## 异常处理

- 未设置环境变量时脚本可在交互式终端隐藏输入密钥；AI 调用时优先自己询问用户，不要启动无法回复的输入等待。
- 401／403：请用户检查或更换密钥。
- 429／余额不足：说明接口错误，停止重复请求。
- 超时或 5xx：告知本次未确认成功，避免自动重试造成重复计费。
- 此模型和 GIF 能力来自该第三方接口的实际测试，不代表 OpenAI 官方模型声明。

## 分享安装

将整个 `dlow-image` 文件夹交给对方。Codex 用户解压到 `~/.codex/skills/`，重新打开会话后可说：“用 dlow-image 生成一个小球弹跳的 GIF。” 其他支持 `SKILL.md` 的 AI 工具按其技能目录规则放置。包内不包含密钥，对方首次使用时由 AI 询问。
