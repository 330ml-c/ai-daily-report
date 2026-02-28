"""
GitHub AI 项目数据抓取模块
负责从 GitHub API 获取活跃的 AI 相关项目
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import requests

try:
    from cache import StarCache
except ImportError:
    from src.cache import StarCache


class GitHubFetcher:
    """GitHub 项目数据抓取器"""

    # 通道化检索配置：聚焦 vibecoding、codex、claude 三个主题
    SEARCH_CHANNELS = {
        "vibecoding": [
            '(vibecoding OR "vibe coding") in:name,description,readme archived:false stars:>10',
            'topic:vibecoding archived:false stars:>10',
        ],
        "codex": [
            '(codex OR "openai codex") in:name,description,readme archived:false stars:>10',
            'topic:codex archived:false stars:>10',
        ],
        "claude": [
            '(claude OR "claude code") in:name,description,readme archived:false stars:>10',
            '(topic:claude OR topic:anthropic) archived:false stars:>10',
        ],
    }

    # 优先级评分权重
    PRIORITY_WEIGHTS = {
        "relevance": 0.55,
        "growth": 0.30,
        "quality": 0.15,
    }
    CHANNEL_ORDER = ["vibecoding", "codex", "claude"]
    CHANNEL_TOP_N = 15
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3

    def __init__(self, github_token: str, cache_dir: str = None):
        """
        初始化 GitHub API 客户端

        Args:
            github_token: GitHub Personal Access Token
            cache_dir: 缓存目录，默认为当前目录下的 star_cache.json
        """
        self.token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }

        # 初始化缓存
        cache_file = os.path.join(cache_dir, "star_cache.json") if cache_dir else "star_cache.json"
        self.cache = StarCache(cache_file)

    def _search_repositories(self, query: str, per_page: int = 20) -> List[Dict]:
        """
        搜索仓库

        Args:
            query: 搜索查询
            per_page: 每页结果数量

        Returns:
            仓库列表
        """
        response = self._http_get(
            f"{self.base_url}/search/repositories",
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page
            },
        )

        if response is None:
            print("  ❌ 搜索失败: 请求异常，已重试")
            return []

        if response.status_code == 200:
            data = response.json()
            return data.get("items", [])
        else:
            print(f"  ❌ 搜索失败: {response.status_code} - {response.text[:100]}")
            return []

    def _http_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        """
        统一封装 GET 请求，提供超时、重试和退避能力
        """
        response = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=self.REQUEST_TIMEOUT
                )
            except requests.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    print(f"  ❌ 请求异常: {e}")
                    return None
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 200:
                return response

            if response.status_code in (403, 429, 500, 502, 503, 504) and attempt < self.MAX_RETRIES - 1:
                retry_seconds = 2 ** attempt
                # GitHub 限流时优先按重置时间等待，避免无效重试
                if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                    reset_at = response.headers.get("X-RateLimit-Reset")
                    if reset_at:
                        try:
                            retry_seconds = max(1, int(reset_at) - int(time.time()))
                        except ValueError:
                            retry_seconds = 2 ** attempt
                time.sleep(min(retry_seconds, 30))
                continue

            return response

        return response

    def _calculate_star_velocity(self, repo_name: str, repo_data: Dict) -> float:
        """
        计算 star 增长速度（每天增长数）

        优先使用缓存中的真实增长数据，如果没有则使用近似计算

        Args:
            repo_name: 项目全名 (owner/repo)
            repo_data: 仓库数据字典

        Returns:
            star 增长速度（每天增长数）
        """
        current_stars = repo_data.get("stargazers_count", 0)

        # 尝试从缓存获取真实增长速度
        growth_rate = self.cache.calculate_growth_rate(repo_name, current_stars)

        if growth_rate is not None:
            # 有缓存数据，返回真实增长速度
            print(f"  📈 {repo_name}: 真实增长 {growth_rate:.1f} stars/天")
            return growth_rate

        # 无缓存数据，使用近似计算
        created_at_str = repo_data.get("created_at", "")
        updated_at_str = repo_data.get("updated_at", "")

        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))

            # 项目存在天数
            days_since_creation = max(1, (datetime.now(updated_at.tzinfo) - created_at).days)

            # 平均每天 star 增长数
            star_velocity = current_stars / days_since_creation

            # 最近更新加成
            days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days
            recency_multiplier = 1.5 if days_since_update < 7 else 1.0

            # 近似增长速度
            estimated_velocity = star_velocity * recency_multiplier

            print(f"  📊 {repo_name}: 估算增长 {estimated_velocity:.1f} stars/天 (创建于 {days_since_creation} 天前)")

            return estimated_velocity

        except Exception as e:
            print(f"  ⚠️  计算 {repo_name} 增长速度失败: {e}")
            return 0

    def _calculate_relevance_score(self, repo_data: Dict) -> Tuple[float, List[str]]:
        """
        计算相关性分数（0-100），并返回命中的主题通道
        """
        repo_name = (repo_data.get("full_name") or "").lower()
        description = (repo_data.get("description") or "").lower()
        topics = [topic.lower() for topic in repo_data.get("topics", [])]
        topics_text = " ".join(topics)

        term_rules = [
            ("vibecoding", ["vibecoding", "vibe coding"]),
            ("codex", ["codex", "openai codex"]),
            ("claude", ["claude", "claude code"]),
        ]

        score = 0.0
        matched_channels = []

        for channel, terms in term_rules:
            channel_matched = False
            for term in terms:
                term_score = 0.0
                if term in repo_name:
                    term_score += 40
                if term in topics_text:
                    term_score += 30
                if term in description:
                    term_score += 18

                if term_score > 0:
                    score += term_score
                    channel_matched = True
                    break

            if channel_matched:
                matched_channels.append(channel)

        if len(matched_channels) > 1:
            score += 10

        return min(score, 100.0), matched_channels

    def _calculate_growth_score(self, star_velocity: float) -> float:
        """
        将 star 增速映射到 0-100 分
        """
        positive_velocity = max(0.0, star_velocity)
        capped_velocity = min(positive_velocity, 50.0)
        return (capped_velocity / 50.0) * 100.0

    def _calculate_quality_score(self, repo_data: Dict) -> float:
        """
        计算项目健康度分数（0-100）
        """
        updated_at_str = repo_data.get("updated_at", "")
        stars = repo_data.get("stargazers_count", 0)

        freshness_score = 30.0
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days
                if days_since_update <= 3:
                    freshness_score = 100.0
                elif days_since_update <= 7:
                    freshness_score = 85.0
                elif days_since_update <= 30:
                    freshness_score = 65.0
                elif days_since_update <= 90:
                    freshness_score = 45.0
                else:
                    freshness_score = 25.0
            except Exception:
                freshness_score = 30.0

        stability_score = (min(max(stars, 0), 5000) / 5000.0) * 100.0
        return freshness_score * 0.6 + stability_score * 0.4

    def _calculate_priority_score(
        self,
        relevance_score: float,
        growth_score: float,
        quality_score: float
    ) -> float:
        """
        计算综合优先级分数
        """
        return (
            relevance_score * self.PRIORITY_WEIGHTS["relevance"] +
            growth_score * self.PRIORITY_WEIGHTS["growth"] +
            quality_score * self.PRIORITY_WEIGHTS["quality"]
        )

    def _extract_repo_info(
        self,
        repo_data: Dict,
        star_velocity: float,
        activity_score: float,
        relevance_score: float = 0.0,
        growth_score: float = 0.0,
        quality_score: float = 0.0,
        matched_channels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        提取仓库信息

        Args:
            repo_data: GitHub API 返回的仓库数据
            star_velocity: star 增长速度
            activity_score: 活跃度分数

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
            "star_velocity": round(star_velocity, 2),
            "activity_score": round(activity_score, 2),
            "relevance_score": round(relevance_score, 2),
            "growth_score": round(growth_score, 2),
            "quality_score": round(quality_score, 2),
            "matched_channels": matched_channels or [],
        }

    def _merge_channels(self, channels_a: List[str], channels_b: List[str]) -> List[str]:
        """
        合并主题通道并按固定顺序输出，保证结果稳定
        """
        merged = set(channels_a).union(set(channels_b))
        ordered_channels = [channel for channel in self.CHANNEL_ORDER if channel in merged]
        others = sorted([channel for channel in merged if channel not in self.CHANNEL_ORDER])
        return ordered_channels + others

    def _select_channel_balanced_projects(self, all_projects: Dict[str, Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        先按通道取 TopN，再合并全局排序，避免单一通道垄断
        """
        selected_projects: Dict[str, Dict[str, Any]] = {}

        for channel in self.CHANNEL_ORDER:
            channel_projects = [
                project for project in all_projects.values()
                if channel in project.get("matched_channels", [])
            ]
            channel_projects.sort(key=lambda project: project["activity_score"], reverse=True)
            for project in channel_projects[:self.CHANNEL_TOP_N]:
                selected_projects[project["name"]] = project

        if len(selected_projects) < limit:
            global_projects = list(all_projects.values())
            global_projects.sort(key=lambda project: project["activity_score"], reverse=True)
            for project in global_projects:
                if project["name"] not in selected_projects:
                    selected_projects[project["name"]] = project
                if len(selected_projects) >= limit:
                    break

        merged_projects = list(selected_projects.values())
        merged_projects.sort(key=lambda project: project["activity_score"], reverse=True)
        return merged_projects[:limit]

    def fetch_active_ai_projects(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        获取活跃的 AI 项目

        Args:
            limit: 获取的项目数量

        Returns:
            项目信息列表，按活跃度排序
        """
        all_projects = {}

        # 第一阶段：按通道召回候选项目
        for channel in self.CHANNEL_ORDER:
            queries = self.SEARCH_CHANNELS.get(channel, [])
            print(f"🔍 搜索通道: {channel}")

            for query in queries:
                repos = self._search_repositories(query, per_page=20)
                print(f"  📦 查询结果 {len(repos)} 个: {query}")

                for repo_data in repos:
                    # 使用项目名称作为唯一标识去重
                    repo_name = repo_data["full_name"]

                    # 计算基础分数
                    star_velocity = self._calculate_star_velocity(repo_name, repo_data)
                    relevance_score, matched_channels = self._calculate_relevance_score(repo_data)
                    matched_channels = self._merge_channels(matched_channels, [channel])
                    growth_score = self._calculate_growth_score(star_velocity)
                    quality_score = self._calculate_quality_score(repo_data)
                    priority_score = self._calculate_priority_score(
                        relevance_score=relevance_score,
                        growth_score=growth_score,
                        quality_score=quality_score
                    )

                    if repo_name in all_projects:
                        # 已存在时合并通道，并保留更高分
                        merged_channels = self._merge_channels(
                            all_projects[repo_name].get("matched_channels", []),
                            matched_channels
                        )

                        if priority_score > all_projects[repo_name]["activity_score"]:
                            info = self._extract_repo_info(
                                repo_data=repo_data,
                                star_velocity=star_velocity,
                                activity_score=priority_score,
                                relevance_score=relevance_score,
                                growth_score=growth_score,
                                quality_score=quality_score,
                                matched_channels=merged_channels,
                            )
                            all_projects[repo_name] = info
                        else:
                            all_projects[repo_name]["matched_channels"] = merged_channels
                        continue

                    # 新项目写入候选池
                    info = self._extract_repo_info(
                        repo_data=repo_data,
                        star_velocity=star_velocity,
                        activity_score=priority_score,
                        relevance_score=relevance_score,
                        growth_score=growth_score,
                        quality_score=quality_score,
                        matched_channels=matched_channels,
                    )
                    all_projects[repo_name] = info

                    print(
                        f"  ✓ 获取: {info['name']} (🎯 {info['relevance_score']} | "
                        f"📈 {info['growth_score']} | 🧪 {info['quality_score']} | "
                        f"📊 {info['activity_score']})"
                    )

        # 第二阶段：通道 TopN 合并后全局排序
        projects = self._select_channel_balanced_projects(all_projects, limit)

        # 更新缓存（保存所有获取到的项目的 star 数）
        print("\n💾 更新缓存...")
        for project in projects:
            self.cache.update_stars(project["name"], project["stars"])
        self.cache.save()

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
            response = self._http_get(
                f"{self.base_url}/repos/{repo_name}/readme"
            )
            if response is None:
                return ""

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
