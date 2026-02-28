#!/usr/bin/env python3
"""
本地测试脚本 - 测试 GitHub 搜索功能
"""

import os
from dotenv import load_dotenv
from github import Github

# 加载环境变量
load_dotenv()

# 使用 Personal Access Token
token = os.getenv("GH_PAT") or os.getenv("GITHUB_TOKEN")

if not token:
    print("❌ 错误：请在 .env 文件中设置 GH_PAT")
    print("   1. 访问 https://github.com/settings/tokens")
    print("   2. 创建 token，勾选 public_repo 权限")
    print("   3. 复制 token 到 .env 文件中的 GH_PAT=")
    exit(1)

print(f"🔑 使用 token: {token[:20]}...")
print()

# 初始化 GitHub 客户端
g = Github(token)

# 检查速率限制
rate_limit = g.get_rate_limit()
print(f"📊 GitHub API 速率限制:")
print(f"  - 剩余搜索次数: {rate_limit.search.remaining}")
print(f"  - 搜索限制重置时间: {rate_limit.search.reset}")
print()

# 测试搜索
print("=" * 50)
print("🔍 测试 GitHub 搜索")
print("=" * 50)

# 测试 1: 简单的关键词搜索
print("\n测试 1: 关键词搜索 'llm'")
try:
    repos = g.search_repositories(query="llm", sort="updated", order="desc", **{"per_page": 5})
    print(f"  找到 {repos.totalCount} 个仓库")

    # 尝试获取前几个
    count = 0
    for repo in repos:
        count += 1
        print(f"  ✓ {repo.full_name} - ⭐ {repo.stargazers_count}")
        if count >= 3:
            break
except Exception as e:
    print(f"  ❌ 错误: {e}")

# 测试 2: topic 搜索
print("\n测试 2: Topic 搜索 'topic:llm'")
try:
    repos = g.search_repositories(query="topic:llm", sort="updated", order="desc", **{"per_page": 5})
    print(f"  找到 {repos.totalCount} 个仓库")

    count = 0
    for repo in repos:
        count += 1
        print(f"  ✓ {repo.full_name} - ⭐ {repo.stargazers_count}")
        if count >= 3:
            break
except Exception as e:
    print(f"  ❌ 错误: {e}")

# 测试 3: 直接获取热门仓库
print("\n测试 3: 直接获取热门 LLM 仓库")
try:
    repo = g.get_repo("microsoft/semantic-kernel")
    print(f"  ✓ {repo.full_name}")
    print(f"    - Stars: {repo.stargazers_count}")
    print(f"    - 描述: {repo.description[:50]}...")
except Exception as e:
    print(f"  ❌ 错误: {e}")

print("\n" + "=" * 50)
print("✅ 测试完成")
print("=" * 50)
