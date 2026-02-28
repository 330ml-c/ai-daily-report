"""
邮件发送模块
负责生成 HTML 邮件并通过 Resend API 发送
"""

import re
from datetime import datetime
from typing import List, Dict, Any
from jinja2 import Environment
import resend


class EmailSender:
    """邮件发送器"""

    def __init__(self, api_key: str):
        """
        初始化 Resend 客户端

        Args:
            api_key: Resend API 密钥
        """
        resend.api_key = api_key

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))

    def _format_summary_to_html(self, summary: str) -> str:
        """
        将摘要文本转换为 HTML，保留代码块格式

        Args:
            summary: 原始摘要文本

        Returns:
            HTML 格式的摘要
        """
        # 先转义 HTML
        html = self._escape_html(summary)
        # 清理常见实体残留
        html = html.replace("&amp;nbsp;", " ").replace("&#160;", " ")

        # 先提取代码块占位，避免后续换行转换污染代码块
        code_blocks = []

        def replace_code_block(match):
            lang = match.group(1)
            code = match.group(2).strip("\n")
            code_blocks.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
            return f"@@CODE_BLOCK_{len(code_blocks) - 1}@@"

        html = re.sub(
            r'```(\w*)\n?(.*?)```',
            replace_code_block,
            html,
            flags=re.DOTALL
        )

        # 转换 Markdown 链接 [text](url)
        html = re.sub(
            r'\[([^\]]+)\]\((https?://[^)\s]+)\)',
            r'<a href="\2" target="_blank">\1</a>',
            html
        )
        # 转换纯 URL
        html = re.sub(
            r'(?<!["\'>])(https?://[^\s<]+)',
            r'<a href="\1" target="_blank">\1</a>',
            html
        )
        # 转换行内代码 `code` 为 <code>
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        # 转换粗体与斜体
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', html)

        # 转换换行
        html = html.replace('\n', '<br>')

        # 恢复代码块
        for idx, block in enumerate(code_blocks):
            html = html.replace(f"@@CODE_BLOCK_{idx}@@", block)

        return html

    def _generate_html_content(self, projects: List[Dict[str, Any]]) -> str:
        """
        生成 HTML 邮件内容

        Args:
            projects: 项目信息列表

        Returns:
            HTML 内容
        """
        template_str = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub AI 项目日报</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .header h1 {
            color: #0366d6;
            margin: 0;
            font-size: 28px;
        }
        .header .date {
            color: #666;
            margin-top: 10px;
            font-size: 14px;
        }
        .intro {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 25px;
            font-size: 14px;
            color: #555;
        }
        .repo {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            background-color: #fafafa;
            transition: box-shadow 0.2s;
        }
        .repo:hover {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        .repo-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .repo-title {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
        }
        .repo-title a {
            color: #0366d6;
            text-decoration: none;
        }
        .repo-title a:hover {
            text-decoration: underline;
        }
        .repo-language {
            display: inline-block;
            padding: 3px 10px;
            background-color: #e1f0ff;
            color: #0366d6;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .repo-description {
            margin: 12px 0;
            color: #555;
            line-height: 1.6;
        }
        .repo-summary {
            margin: 12px 0;
            padding: 12px;
            background-color: #f0f7ff;
            border-left: 3px solid #0366d6;
            border-radius: 0 4px 4px 0;
            font-size: 14px;
            color: #444;
        }
        .repo-summary a {
            color: #0366d6;
            text-decoration: underline;
            word-break: break-all;
        }
        /* 代码块样式 */
        .repo-summary pre {
            background-color: #f6f8fa;
            border: 1px solid #d1d5da;
            border-radius: 6px;
            padding: 12px;
            overflow-x: auto;
            margin: 10px 0;
        }
        .repo-summary code {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 13px;
            line-height: 1.45;
            background-color: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .repo-summary pre code {
            background-color: transparent;
            padding: 0;
            border-radius: 0;
        }
        .repo-stats {
            display: flex;
            gap: 20px;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        .stat {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 14px;
            color: #666;
        }
        .stat-icon {
            font-size: 16px;
        }
        .stat-value {
            font-weight: 600;
            color: #0366d6;
        }
        .repo-topics {
            margin-top: 12px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .topic {
            padding: 4px 12px;
            background-color: #f0f0f0;
            color: #555;
            border-radius: 12px;
            font-size: 12px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #888;
            font-size: 12px;
        }
        .footer a {
            color: #0366d6;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 GitHub AI 项目日报</h1>
            <div class="date">{{ date }}</div>
        </div>

        <div class="intro">
            <strong>今日摘要：</strong>为您精选 {{ total_count }} 个最活跃的 AI 相关项目，
            涵盖 MCP、Agent、LangChain 等 AI Coding 热门领域。
        </div>

        {% for repo in projects %}
        <div class="repo">
            <div class="repo-header">
                <h2 class="repo-title">
                    <a href="{{ repo.url }}">{{ repo.name }}</a>
                </h2>
                {% if repo.language %}
                <span class="repo-language">{{ repo.language }}</span>
                {% endif %}
            </div>

            {% if repo.description %}
            <p class="repo-description">{{ repo.description }}</p>
            {% endif %}

            {% if repo.summary %}
            <div class="repo-summary">
                <strong>📋 项目简介：</strong>{{ repo.summary_html | safe }}
            </div>
            {% endif %}

            <div class="repo-stats">
                <div class="stat">
                    <span class="stat-icon">⭐</span>
                    <span><span class="stat-value">{{ repo.stars | format_number }}</span> Stars</span>
                </div>
                <div class="stat">
                    <span class="stat-icon">🍴</span>
                    <span>{{ repo.forks | format_number }} Forks</span>
                </div>
                {% if repo.star_velocity %}
                <div class="stat">
                    <span class="stat-icon">📈</span>
                    <span><span class="stat-value">{{ repo.star_velocity }}</span> stars/天</span>
                </div>
                {% endif %}
                <div class="stat">
                    <span class="stat-icon">🕒</span>
                    <span>更新于 {{ repo.updated_at | format_date }}</span>
                </div>
            </div>

            {% if repo.topics %}
            <div class="repo-topics">
                {% for topic in repo.topics[:5] %}
                <span class="topic">{{ topic }}</span>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endfor %}

        <div class="footer">
            <p>本邮件由 <a href="https://github.com">GitHub Actions</a> 自动生成</p>
            <p>如有问题或建议，请联系管理员</p>
        </div>
    </div>
</body>
</html>
        """

        # 为每个项目生成 HTML 格式的摘要
        for project in projects:
            if 'summary' in project and project['summary']:
                project['summary_html'] = self._format_summary_to_html(project['summary'])

        # 创建环境并注册过滤器
        env = Environment()
        env.filters["format_number"] = lambda x: f"{x:,}"
        env.filters["format_date"] = lambda x: datetime.fromisoformat(
            x
        ).strftime("%Y-%m-%d")

        # 从字符串创建模板
        template = env.from_string(template_str)

        # 渲染模板
        return template.render(
            date=datetime.now().strftime("%Y年%m月%d日"),
            projects=projects,
            total_count=len(projects),
        )

    def send_report(
        self,
        to_email: str,
        projects: List[Dict[str, Any]],
        save_html: bool = True,
    ) -> bool:
        """
        发送日报邮件

        Args:
            to_email: 收件人邮箱
            projects: 项目信息列表
            save_html: 是否保存 HTML 到文件

        Returns:
            发送是否成功
        """
        try:
            # 生成 HTML 内容
            html_content = self._generate_html_content(projects)

            # 保存 HTML 到文件（用于调试和 artifact）
            if save_html:
                with open("report.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("📄 HTML 报告已保存到 report.html")

            # 发送邮件
            # 注意：需要在 Resend 验证域名后才能发送
            # 免费测试：只能发送到注册 Resend 的邮箱
            # 完整功能：需在 https://resend.com/domains 添加并验证你的域名
            params = {
                "from": "AI Daily Report <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"🤖 GitHub AI 项目日报 - {datetime.now().strftime('%Y-%m-%d')}",
                "html": html_content,
            }

            r = resend.Emails.send(params)

            if r.get("id"):
                print(f"✅ 邮件发送成功！ID: {r['id']}")
                return True
            else:
                print(f"❌ 邮件发送失败: {r}")
                return False

        except Exception as e:
            print(f"❌ 发送邮件时出错: {e}")
            # 即使发送失败，HTML 文件已保存，可以作为降级方案
            return False


def format_number(num: int) -> str:
    """格式化数字，添加千分位分隔符"""
    return f"{num:,}"
