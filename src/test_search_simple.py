#!/usr/bin/env python3
"""
本地联调脚本 - 使用 requests 直接调用 GitHub API
注意：该文件用于手动联调，不作为单元测试执行
"""

import os
import requests
from dotenv import load_dotenv


def main():
    """脚本入口"""
    load_dotenv()

    token = os.getenv("GH_PAT")
    if not token or token == "your_token_here":
        print("❌ 错误：GH_PAT 未设置")
        return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    print("=" * 50)
    print("🔍 测试 GitHub 搜索 API")
    print("=" * 50)

    print("\n测试 1: 关键词搜索 'llm'")
    response = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": "llm", "sort": "updated", "order": "desc", "per_page": 3},
        headers=headers
    )
    print(f"  状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  找到 {data.get('total_count', 0)} 个仓库")
        for item in data.get('items', [])[:3]:
            print(f"  ✓ {item['full_name']} - ⭐ {item['stargazers_count']}")
    else:
        print(f"  ❌ 错误: {response.text[:200]}")

    print("\n测试 2: Topic 搜索 'topic:llm'")
    response = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": "topic:llm", "sort": "updated", "order": "desc", "per_page": 3},
        headers=headers
    )
    print(f"  状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  找到 {data.get('total_count', 0)} 个仓库")
        for item in data.get('items', [])[:3]:
            print(f"  ✓ {item['full_name']} - ⭐ {item['stargazers_count']}")
    else:
        print(f"  ❌ 错误: {response.text[:200]}")

    print("\n测试 3: 获取 microsoft/semantic-kernel")
    response = requests.get(
        "https://api.github.com/repos/microsoft/semantic-kernel",
        headers=headers
    )
    print(f"  状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ {data['full_name']}")
        print(f"    - Stars: {data['stargazers_count']}")
        print(f"    - 描述: {data.get('description', 'N/A')[:50]}...")
    else:
        print(f"  ❌ 错误: {response.text[:200]}")

    print("\n测试 4: 搜索不同的主题")
    topics = ["llm", "mcp", "langchain", "agent", "openai"]
    for topic in topics:
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": f"topic:{topic}", "per_page": 1},
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            count = data.get('total_count', 0)
            print(f"  topic:{topic} -> 找到 {count} 个仓库")
        else:
            print(f"  topic:{topic} -> 失败")

    print("\n" + "=" * 50)
    print("✅ 测试完成")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
