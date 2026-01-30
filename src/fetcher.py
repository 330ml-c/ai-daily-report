"""
GitHub AI 项目数据抓取模块
负责从 GitHub API 获取活跃的 AI 相关项目
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from github import Github
from github.Repository import Repository


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
        self.github = Github(github_token)
        self.rate_limit = self.github.get_rate_limit()

    def _build_search_query(self) -> str:
        """构建 GitHub 搜索查询"""
        # 组合多个 topic 进行搜索
        topic_queries = [f"topic:{topic}" for topic in self.SEARCH_TOPICS]
        return " OR ".join(topic_queries)

    def _calculate_activity_score(self, repo: Repository) -> float:
        """
        计算仓库活跃度分数

        综合考虑：
        - Star 数 (权重 0.3)
        - Fork 数 (权重 0.2)
        - 最近更新时间 (权重 0.3)
        - Open Issues/PRs 数量 (权重 0.2)

        Args:
            repo: GitHub Repository 对象

        Returns:
            活跃度分数 (越高越活跃)
        """
        # 基础分数
        stars = repo.stargazers_count
        forks = repo.forks_count
        open_issues = repo.get_issues(state="open").totalCount

        # 最近更新时间分数 (30天内更新的项目得分更高)
        updated_at = repo.updated_at
        days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days
        recency_score = max(0, 100 - days_since_update)  # 0-100 分

        # 综合计算
        activity_score = (
            stars * 0.3 +
            forks * 0.2 +
            recency_score * 10 +
            open_issues * 0.2
        )

        return activity_score

    def _extract_repo_info(self, repo: Repository) -> Dict[str, Any]:
        """
        提取仓库信息

        Args:
            repo: GitHub Repository 对象

        Returns:
            仓库信息字典
        """
        return {
            "name": repo.full_name,
            "description": repo.description or "暂无描述",
            "url": repo.html_url,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "open_issues": repo.open_issues_count,
            "language": repo.language or "Unknown",
            "created_at": repo.created_at.isoformat(),
            "updated_at": repo.updated_at.isoformat(),
            "topics": repo.get_topics(),
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

            try:
                # 搜索仓库
                repositories = self.github.search_repositories(
                    query=query,
                    sort="updated",
                    order="desc",
                    **{"per_page": 20}  # 每个主题取 20 个
                )

                # 获取总数
                total_count = repositories.totalCount
                print(f"  📊 找到 {total_count} 个仓库")

                repo_list = list(repositories)
                print(f"  📦 获取到 {len(repo_list)} 个仓库对象")

                for repo in repo_list:
                    try:
                        # 检查速率限制
                        remaining = self.github.get_rate_limit().search.remaining
                        if remaining < 50:
                            print(f"⚠️  API 速率限制即将耗尽，剩余: {remaining}")
                            break

                        # 使用项目名称作为唯一标识去重
                        if repo.full_name not in all_projects:
                            info = self._extract_repo_info(repo)
                            info["activity_score"] = self._calculate_activity_score(repo)
                            all_projects[repo.full_name] = info
                            print(f"  ✓ 获取: {info['name']} (⭐ {info['stars']})")

                    except Exception as e:
                        print(f"  ❌ 获取仓库信息失败 {repo.full_name}: {e}")
                        continue

            except Exception as e:
                print(f"❌ 搜索主题 {topic} 失败: {e}")
                continue

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
            repo = self.github.get_repo(repo_name)
            readme = repo.get_readme()
            content = readme.decoded_content.decode("utf-8")
            return content
        except Exception as e:
            print(f"⚠️  获取 README 失败 {repo_name}: {e}")
            return ""
