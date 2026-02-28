# GitHub AI Coding 项目日报

自动抓取 GitHub 上最活跃的 **AI Coding** 相关项目，每天早上发送邮件报告。

## 功能特点

- 🔍 自动搜索 GitHub 上的 AI Coding 热门项目（MCP、Agent、LangChain、Claude、Copilot 等）
- 📈 **智能增长速度算法**：优先推荐短时间 star 增长快的项目，兼顾成熟热门项目
- 💾 **历史缓存对比**：每次运行后缓存 star 数据，下次计算真实增长速度
- 📝 智能提取项目简介（保留短代码块）
- 📧 每天早上 8:00 自动发送 HTML 邮件报告
- 🎨 精美邮件模板，支持代码高亮显示
- 🚀 基于 GitHub Actions，无需服务器

## 快速开始

### 1. Fork 本仓库

点击右上角的 Fork 按钮

### 2. 配置 GitHub Secrets

在你的仓库中设置以下 Secrets（Settings → Secrets and variables → Actions）：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `GH_PAT` | GitHub Personal Access Token | [创建 Token](https://github.com/settings/tokens)，需要 `public_repo` 权限 |
| `RESEND_API_KEY` | Resend 邮件服务密钥 | [注册 Resend](https://resend.com/api-keys) 并获取 API Key（免费 3000 封/月） |
| `TO_EMAIL` | 接收邮件的地址 | 你要接收报告的邮箱地址 |

**注意**：
- `GH_PAT` 必须使用 Personal Access Token，GitHub Actions 提供的 `GITHUB_TOKEN` 有搜索限制
- 使用 Resend 免费测试域名 `onboarding@resend.dev` 只能发送到注册 Resend 的邮箱

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
│   ├── cache.py                   # Star 历史数据缓存模块
│   ├── fetcher.py                 # GitHub API 数据抓取（含增长速度计算）
│   ├── summarizer.py              # README 内容总结（保留代码块）
│   ├── sender.py                  # 邮件发送（支持代码高亮）
│   ├── main.py                    # 主程序入口
│   └── test_search_simple.py      # API 测试脚本
├── star_cache.json                # Star 历史缓存（自动生成）
├── requirements.txt               # Python 依赖（requests、jinja2、resend）
├── .env.example                   # 环境变量示例
└── README.md                      # 项目文档
```

## 工作原理

### 1. 数据抓取

- 使用 `requests` 直接调用 GitHub Search API
- 采用**双阶段检索**：
  - 第一阶段：按通道召回（`vibecoding` / `codex` / `claude`）
  - 第二阶段：按综合优先级分数精排
- 每个通道使用 2 条查询语句，每条最多获取 20 个仓库，最终合并去重

### 2. 优先级评分模型

**核心创新**：先保证主题相关性，再综合增长速度与项目健康度

```python
# 有缓存时：计算真实增长速度
if cached_stars:
    growth_rate = (current_stars - cached_stars) / days_diff
else:
    # 无缓存时：近似估算
    growth_rate = (stars / days_since_creation) * recency_bonus

# 子分数
relevance_score = 关键词命中分(name/topics/description)
growth_score = star_velocity 映射分
quality_score = 最近更新时间 + star 稳定度

# 综合优先级分数
priority_score = relevance_score * 0.55 + growth_score * 0.30 + quality_score * 0.15
```

**工作原理**：
- **首次运行**：使用"平均 star/天 × 更新加成"估算
- **后续运行**：使用缓存的 star 数据计算真实增长速度
- **排序结果**：优先展示 `vibecoding` / `codex` / `claude` 高相关项目，再平衡增长和质量

### 3. 摘要生成

- 通过 GitHub API 获取项目的 README.md 内容（base64 解码）
- **保留短代码块**（3 行以内），移除长代码块
- 清理 Markdown 格式（图片、长链接等）
- 提取有意义的简介段落
- 限制在 500 字符以内

### 4. 邮件发送

- 使用 Jinja2 生成精美的 HTML 邮件模板
- **支持代码块高亮显示**
- 显示 star 增长速度（stars/天）
- 通过 Resend API 发送邮件
- 失败时保存 HTML 文件作为 artifact

## 配置说明

### 修改搜索主题

编辑 `src/fetcher.py` 中的 `SEARCH_CHANNELS` 配置：

```python
SEARCH_CHANNELS = {
    "vibecoding": [
        '(vibecoding OR "vibe coding") in:name,description,readme archived:false stars:>10',
        "topic:vibecoding archived:false stars:>10",
    ],
    "codex": [
        '(codex OR "openai codex") in:name,description,readme archived:false stars:>10',
    ],
    "claude": [
        '(claude OR "claude code") in:name,description,readme archived:false stars:>10',
    ],
}
```

### 调整活跃度公式

编辑 `src/fetcher.py` 中的 `PRIORITY_WEIGHTS`：

```python
PRIORITY_WEIGHTS = {
    "relevance": 0.55,
    "growth": 0.30,
    "quality": 0.15,
}
```

### 修改发送时间

编辑 `.github/workflows/daily-ai-report.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 时间，北京时间需 +8 小时
```

### 修改邮件模板

编辑 `src/sender.py` 中的 `_generate_html_content` 方法的 HTML 模板。

### 配置 Resend 域名

默认使用 Resend 的测试域名 `onboarding@resend.dev`，只能发送到注册邮箱。

如需发送到任意邮箱，需要：
1. 在 https://resend.com/domains 添加并验证你的域名
2. 修改 `src/sender.py` 中的 `from` 地址为你的域名

```python
"from": "AI Daily Report <noreply@yourdomain.com>",
```

## 常见问题

### Q: 为什么没有收到邮件？

A: 请检查：
1. GitHub Actions 是否成功运行（查看 Actions 页面）
2. `GH_PAT` 是否正确配置（必须是 Personal Access Token）
3. Resend API Key 是否正确
4. 邮箱地址是否正确
5. 查看垃圾邮件文件夹

### Q: GitHub API 速率限制？

A: 使用 Personal Access Token（`GH_PAT`），速率限制为 5000 次/小时，足够每天使用。

### Q: 如何自定义接收时间？

A: 修改 cron 表达式。例如：
- `0 1 * * *` - UTC 1:00（北京时间 9:00）
- `0 22 * * *` - UTC 22:00（北京时间次日 6:00）

### Q: 搜索结果为空？

A: 确保配置了 `GH_PAT` Secret。GitHub Actions 提供的 `GITHUB_TOKEN` 有搜索 API 限制。

### Q: star_cache.json 是什么？

A: 这是 star 历史缓存文件，用于计算真实的 star 增长速度。首次运行后会自动生成，每次运行后更新。删除它将重新开始计算。

### Q: 邮件中的代码块显示不正常？

A: 已更新邮件模板支持代码块样式。如果仍有问题，请检查邮件客户端是否支持 CSS（部分邮件客户端对 CSS 支持有限）。

## 更新日志

### v2.0 (当前版本)

- ✨ 新增：Star 增长速度算法，优先推荐增长快的项目
- ✨ 新增：历史缓存对比，计算真实增长速度
- ✨ 新增：邮件模板支持代码块高亮显示
- 🎯 优化：搜索关键词聚焦 AI Coding 领域
- 🎯 优化：保留摘要中的短代码块
- 🐛 修复：Python 3.8 兼容性问题

### v1.0

- 基础功能：GitHub 项目搜索和邮件发送

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
