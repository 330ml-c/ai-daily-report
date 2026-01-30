"""
GitHub AI 项目数据抓取模块
负责从 GitHub API 获取活跃的 AI 相关项目
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests


class GitHubFetcher:
    """GitHub 项目数据抓取器"""

    # AI 相关的搜索关键词
    SEARCH_TOPICS = [
        "llm",
        "mcp",
        "langchain",
        "agent",
        "openai",
        "anthropic",
        "machine-learning",
        "deep-learning",
    ]

    def __init__(self, github_token: str):
        """
        初始化 GitHub API 客户端

        Args:
            github_token: GitHub Personal Access Token
        """
        self.token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }

    def _search_repositories(self, query: str, per_page: int = 20) -> List[Dict]:
        """
        搜索仓库

        Args:
            query: 搜索查询
            per_page: 每页结果数量

        Returns:
            仓库列表
        """
        response = requests.get(
            f"{self.base_url}/search/repositories",
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page
            },
            headers=self.headers
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("items", [])
        else:
            print(f"  ❌ 搜索失败: {response.status_code} - {response.text[:100]}")
            return []

    def _calculate_activity_score(self, repo_data: Dict) -> float:
        """
        计算仓库活跃度分数

        综合考虑：
        - Star 数 (权重 0.3)
        - Fork 数 (权重 0.2)
        - 最近更新时间 (权重 0.3)
        - Open Issues 数量 (权重 0.2)

        Args:
            repo_data: 仓库数据字典

        Returns:
            活跃度分数 (越高越活跃)
        """
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        open_issues = repo_data.get("open_issues_count", 0)

        # 最近更新时间分数
        updated_at_str = repo_data.get("updated_at", "")
        try:
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days
            recency_score = max(0, 100 - days_since_update)
        except:
            recency_score = 50  # 默认分数

        # 综合计算
        activity_score = (
            stars * 0.3 +
            forks * 0.2 +
            recency_score * 10 +
            open_issues * 0.2
        )

        return activity_score

    def _extract_repo_info(self, repo_data: Dict) -> Dict[str, Any]:
        """
        提取仓库信息

        Args:
            repo_data: GitHub API 返回的仓库数据

        Returns:
            仓库信息字典
        """
        return {
            "name": repo_data["full_name"],
            "description": repo_data.get("description") or "暂无描述",
            "url": repo_data["html_url"],
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": repo_data.get("language") or "Unknown",
            "created_at": repo_data.get("created_at", ""),
            "updated_at": repo_data.get("updated_at", ""),
            "topics": repo_data.get("topics", []),
        }

    def fetch_active_ai_projects(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        获取活跃的 AI 项目

        Args:
            limit: 获取的项目数量

        Returns:
            项目信息列表，按活跃度排序
        """
        all_projects = {}

        # 分别搜索每个主题，然后合并去重
        for topic in self.SEARCH_TOPICS[:4]:  # 只搜索前4个主题以节省 API 配额
            query = f"topic:{topic}"

            print(f"🔍 搜索主题: {topic}")

            repos = self._search_repositories(query, per_page=20)
            print(f"  📦 获取到 {len(repos)} 个仓库")

            for repo_data in repos:
                # 使用项目名称作为唯一标识去重
                repo_name = repo_data["full_name"]
                if repo_name not in all_projects:
                    info = self._extract_repo_info(repo_data)
                    info["activity_score"] = self._calculate_activity_score(repo_data)
                    all_projects[repo_name] = info
                    print(f"  ✓ 获取: {info['name']} (⭐ {info['stars']})")

        # 转换为列表并按活跃度排序
        projects = list(all_projects.values())
        projects.sort(key=lambda x: x["activity_score"], reverse=True)

        return projects[:limit]

    def get_readme_content(self, repo_name: str) -> str:
        """
        获取仓库的 README 内容

        Args:
            repo_name: 仓库全名 (owner/repo)

        Returns:
            README 内容 (Markdown 格式)
        """
        try:
            # 先尝试获取 README 文件
            response = requests.get(
                f"{self.base_url}/repos/{repo_name}/readme",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                # README 内容是 base64 编码的
                import base64
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content
            else:
                return ""
        except Exception as e:
            print(f"  ⚠️  获取 README 失败 {repo_name}: {e}")
            return ""
