# Mailbox Agent

面向 QQ 邮箱、网易 163/126 邮箱和 139 邮箱的本地只读 Agent。网页端配置一个邮箱账号后，应用会用 IMAP 拉取 `UNSEEN` 邮件，不改服务器已读标记，按白名单处理，并用 LangGraph 生成摘要、分类、风险提示和回复草稿。应用不会自动发送邮件。

## 运行

在项目目录执行：

```powershell
python -m uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000`。依赖已经存在时无需再次安装；全新环境可使用 `pip install -e ".[dev]"`。

## 页面配置

- Provider：选择 QQ、NetEase (163/126) 或 139。
- IMAP authorization code：填写邮箱后台生成的授权码，不是网页登录密码。
- Allowed senders：填写允许处理的发件人地址，多个地址用逗号分隔；为空时拒绝所有邮件。
- Model endpoint / key / model：填写任意 OpenAI 兼容服务的地址、密钥和模型名。
- Grant access：未勾选时不会建立 IMAP 连接。
- Polling interval：选择手动或每分钟、5 分钟、15 分钟轮询。

授权码、模型 API Key 使用 Windows DPAPI 加密后保存在本机 SQLite。只有当前 Windows 用户、当前电脑能够解密；网页从不回显密钥。首次升级到 `v0.1.2` 后需要重新填写并保存一次，之后重启服务无需重复输入。

## 邮件行为

- 每次检查从 INBOX 获取 `UNSEEN` 邮件，并使用 `mark_seen=False`，所以不会改动邮箱服务器的已读状态。
- 使用 `UIDVALIDITY + UID` 记录已处理邮件，重试和重启不会重复调用 Agent。
- 对每个允许发件人，最多回溯收件箱和已发送文件夹中最近三封邮件作为上下文。
- 识别出包含中文或英文验证码关键词和数字验证码的邮件后，同一发件人只保留最新一封；超过一小时的旧邮件会移动到邮箱的 Trash/垃圾箱，不做永久删除。清理会扫描整个 INBOX，不受未读状态和最近 100 封限制。
- 只显示摘要和回复草稿，不调用 SMTP，不会自动发送。

## LangSmith 调试

项目根目录的 `.env` 支持以下变量，`.env` 已被 Git 忽略：

```text
LANGSMITH_TRACING_V2=true
LANGSMITH_API_KEY=你的新密钥
LANGSMITH_PROJECT=cn-mail-agent
```

操作步骤：

1. 在 LangSmith 控制台创建或选择 `cn-mail-agent` 项目。
2. 在本机 `.env` 写入新的 API Key。不要把密钥写入代码或提交到 GitHub。
3. 启动应用并点击一次 `Check now`。
4. 在 LangSmith 的项目中打开最新 Run，查看 LangGraph 节点、模型输入输出、延迟和错误。
5. 若调用失败，先查看 Run 的错误信息；常见原因是兼容地址需要包含 `/v1`、模型名不正确或服务商不接受当前 JSON 输出提示。

## 测试

```powershell
python -m pytest tests -v -p no:cacheprovider
```

测试使用假的 IMAP 网关和模型，不会访问真实邮箱或消耗模型额度。
