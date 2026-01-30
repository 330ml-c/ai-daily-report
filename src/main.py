#!/usr/bin/env python3
"""
GitHub AI 项目日报主程序
每天自动抓取最活跃的 AI 相关项目并发送邮件报告
"""

import os
import sys
from dotenv import load_dotenv

from fetcher import GitHubFetcher
from summarizer import ReadmeSummarizer
from sender import EmailSender


def main():
    """主函数"""
    print("=" * 50)
    print("🤖 GitHub AI 项目日报生成器 v2.0")
    print("=" * 50)

    # 加载环境变量
    load_dotenv()

    # 从环境变量获取配置
    # 优先使用 Personal Access Token，因为 GITHUB_TOKEN 有搜索限制
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    resend_api_key = os.getenv("RESEND_API_KEY")
    to_email = os.getenv("TO_EMAIL")

    # 验证必需的环境变量
    if not all([github_token, resend_api_key, to_email]):
        print("❌ 错误：缺少必需的环境变量")
        print("请设置以下环境变量：")
        print("  - GITHUB_TOKEN")
        print("  - RESEND_API_KEY")
        print("  - TO_EMAIL")
        sys.exit(1)

    print(f"📧 目标邮箱: {to_email}")
    print()

    # 初始化组件
    print("🔧 初始化组件...")
    fetcher = GitHubFetcher(github_token)
    summarizer = ReadmeSummarizer()
    sender = EmailSender(resend_api_key)
    print("✅ 组件初始化完成")
    print()

    # 抓取项目数据
    print("🔍 开始抓取 AI 项目数据...")
    projects = fetcher.fetch_active_ai_projects(limit=30)
    print(f"✅ 共获取 {len(projects)} 个项目")
    print()

    # 筛选并处理项目（取前 15 个）
    top_projects = projects[:15]
    print(f"📊 筛选出前 {len(top_projects)} 个最活跃的项目")
    print()

    # 为每个项目生成摘要
    print("📝 生成项目摘要...")
    for i, project in enumerate(top_projects, 1):
        print(f"  [{i}/{len(top_projects)}] 处理: {project['name']}")

        # 获取 README 内容
        readme = fetcher.get_readme_content(project["name"])

        # 生成摘要
        if readme:
            summary = summarizer.summarize(readme, max_length=300)
            project["summary"] = summary
        else:
            project["summary"] = project.get("description", "")

    print("✅ 摘要生成完成")
    print()

    # 发送邮件
    print("📧 发送邮件报告...")
    success = sender.send_report(
        to_email=to_email,
        projects=top_projects,
        save_html=True,
    )

    print()
    print("=" * 50)
    if success:
        print("✅ 日报生成并发送成功！")
    else:
        print("⚠️  邮件发送失败，但 HTML 报告已保存到 report.html")
    print("=" * 50)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
