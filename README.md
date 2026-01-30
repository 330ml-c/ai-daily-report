# GitHub AI 项目日报

自动抓取 GitHub 上最活跃的 AI 相关项目，每天早上发送邮件报告。

## 功能特点

- 🔍 自动搜索 GitHub 上的 AI 热门项目（LLM、MCP、LangChain、Agent 等）
- 📊 综合计算活跃度（stars、forks、更新频率、issue 数量）
- 📝 智能提取项目简介（基于 README 内容）
- 📧 每天早上 8:00 自动发送 HTML 邮件报告
- 🚀 基于 GitHub Actions，无需服务器

## 快速开始

### 1. Fork 本仓库

点击右上角的 Fork 按钮

### 2. 配置 GitHub Secrets

在你的仓库中设置以下 Secrets（Settings → Secrets and variables → Actions）：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `GITHUB_TOKEN` | GitHub 访问令牌 | [创建 Token](https://github.com/settings/tokens)，需要 `public_repo` 权限 |
| `RESEND_API_KEY` | Resend 邮件服务密钥 | [注册 Resend](https://resend.com/api-keys) 并获取 API Key（免费 3000 封/月） |
| `TO_EMAIL` | 接收邮件的地址 | 你要接收报告的邮箱地址 |

### 3. 启用 GitHub Actions

- 进入仓库的 Actions 页面
- 点击 "I understand my workflows, go ahead and enable them"

### 4. 手动测试（可选）

在 Actions 页面选择 "Daily AI Projects Report" workflow，点击 "Run workflow" 进行手动测试。

### 5. 等待每日报告

GitHub Actions 会每天 UTC 0:00（北京时间 8:00）自动运行并发送邮件。

## 本地开发

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

### 运行

```bash
python src/main.py
```

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── daily-ai-report.yml    # GitHub Actions 配置
├── src/
│   ├── fetcher.py                 # GitHub API 数据抓取
│   ├── summarizer.py              # README 内容总结
│   ├── sender.py                  # 邮件发送
│   └── main.py                    # 主程序入口
├── requirements.txt               # Python 依赖
├── .env.example                   # 环境变量示例
└── README.md                      # 项目文档
```

## 工作原理

### 1. 数据抓取

- 使用 GitHub Search API 搜索 AI 相关项目
- 搜索关键词：`topic:llm OR topic:mcp OR topic:langchain OR topic:agent`
- 按更新时间排序，获取最新的 30 个项目

### 2. 活跃度计算

综合多个因素计算项目活跃度：

```python
activity_score = (
    stars × 0.3 +
    forks × 0.2 +
    近期更新分数 × 10 +
    open_issues × 0.2
)
```

### 3. 摘要生成

- 获取项目的 README.md 内容
- 清理 Markdown 格式（图片、代码块等）
- 提取有意义的简介段落
- 限制在 300 字符以内

### 4. 邮件发送

- 使用 Jinja2 生成 HTML 邮件模板
- 通过 Resend API 发送邮件
- 失败时保存 HTML 文件作为 artifact

## 配置说明

### 修改搜索主题

编辑 `src/fetcher.py` 中的 `SEARCH_TOPICS` 列表：

```python
SEARCH_TOPICS = [
    "llm",
    "mcp",
    "langchain",
    # 添加你感兴趣的主题
]
```

### 修改发送时间

编辑 `.github/workflows/daily-ai-report.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 时间，北京时间需 +8 小时
```

### 修改邮件模板

编辑 `src/sender.py` 中的 `_generate_html_content` 方法的 HTML 模板。

## 常见问题

### Q: 为什么没有收到邮件？

A: 请检查：
1. GitHub Actions 是否成功运行（查看 Actions 页面）
2. Resend API Key 是否正确
3. 邮箱地址是否正确
4. 查看垃圾邮件文件夹

### Q: GitHub API 速率限制？

A: 本项目使用 GitHub Token，速率限制为 5000 次/小时，足够每天使用。如果遇到限制，请检查 Token 是否正确配置。

### Q: 如何自定义接收时间？

A: 修改 cron 表达式。例如：
- `0 1 * * *` - UTC 1:00（北京时间 9:00）
- `0 22 * * *` - UTC 22:00（北京时间次日 6:00）

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
