"""
Star 历史数据缓存模块
用于计算项目的 star 增长速度
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional


class StarCache:
    """Star 历史数据缓存管理器"""

    def __init__(self, cache_file: str = "star_cache.json"):
        """
        初始化缓存管理器

        Args:
            cache_file: 缓存文件路径
        """
        self.cache_file = cache_file
        self.cache: Dict[str, Dict] = {}
        self._load_cache()

    def _load_cache(self):
        """从文件加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                print(f"✓ 已加载缓存，包含 {len(self.cache)} 个项目的历史数据")
            except Exception as e:
                print(f"⚠️  加载缓存失败: {e}")
                self.cache = {}
        else:
            print("ℹ️  缓存文件不存在，首次运行将创建新缓存")
            self.cache = {}

    def _save_cache(self):
        """保存缓存到文件"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"✓ 已保存缓存，包含 {len(self.cache)} 个项目")
        except Exception as e:
            print(f"⚠️  保存缓存失败: {e}")

    def get_stars(self, repo_name: str) -> Optional[int]:
        """
        获取项目的历史 star 数

        Args:
            repo_name: 项目全名 (owner/repo)

        Returns:
            历史 star 数，如果不存在则返回 None
        """
        if repo_name in self.cache:
            return self.cache[repo_name].get("stars")
        return None

    def get_cached_time(self, repo_name: str) -> Optional[datetime]:
        """
        获取缓存的记录时间

        Args:
            repo_name: 项目全名 (owner/repo)

        Returns:
            缓存时间，如果不存在则返回 None
        """
        if repo_name in self.cache:
            time_str = self.cache[repo_name].get("timestamp")
            if time_str:
                return datetime.fromisoformat(time_str)
        return None

    def update_stars(self, repo_name: str, stars: int):
        """
        更新项目的 star 数到缓存

        Args:
            repo_name: 项目全名 (owner/repo)
            stars: 当前 star 数
        """
        self.cache[repo_name] = {
            "stars": stars,
            "timestamp": datetime.now().isoformat()
        }

    def save(self):
        """保存缓存到文件"""
        self._save_cache()

    def calculate_growth_rate(
        self,
        repo_name: str,
        current_stars: int,
        current_time: Optional[datetime] = None
    ) -> Optional[float]:
        """
        计算项目的 star 增长速度（每天增长数）

        Args:
            repo_name: 项目全名 (owner/repo)
            current_stars: 当前 star 数
            current_time: 当前时间，默认使用当前系统时间

        Returns:
            每天增长数，如果没有缓存数据则返回 None
        """
        cached_stars = self.get_stars(repo_name)
        cached_time = self.get_cached_time(repo_name)

        if cached_stars is None or cached_time is None:
            return None

        if current_time is None:
            current_time = datetime.now()

        # 计算时间差（天数）
        time_diff = (current_time - cached_time).total_seconds() / 86400  # 转换为天数

        if time_diff <= 0:
            return 0

        # 计算 star 增长数
        star_growth = current_stars - cached_stars

        # 每天增长数
        growth_rate = star_growth / time_diff

        return growth_rate
