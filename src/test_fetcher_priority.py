#!/usr/bin/env python3
"""
fetcher 优先级排序单元测试
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fetcher import GitHubFetcher


class GitHubFetcherPriorityTest(unittest.TestCase):
    """GitHubFetcher 排序相关测试"""

    def setUp(self):
        self.fetcher = GitHubFetcher("dummy-token")

    def test_relevance_score_should_focus_on_claude_codex_vibecoding(self):
        """命中核心关键词时应获得高相关性分数"""
        repo_data = {
            "full_name": "demo/claude-code-assistant",
            "description": "A coding assistant powered by claude model",
            "topics": ["ai", "coding", "claude"],
        }

        relevance_score, matched_channels = self.fetcher._calculate_relevance_score(repo_data)

        self.assertGreaterEqual(relevance_score, 60)
        self.assertIn("claude", matched_channels)

    def test_priority_score_should_use_relevance_growth_quality_weights(self):
        """优先级分数应按既定权重融合三个子分数"""
        priority_score = self.fetcher._calculate_priority_score(
            relevance_score=80,
            growth_score=50,
            quality_score=40,
        )

        self.assertAlmostEqual(priority_score, 65.0)

    def test_merge_channels_should_keep_stable_order(self):
        """通道合并应保持固定顺序，避免集合无序带来的抖动"""
        merged_channels = self.fetcher._merge_channels(
            ["claude", "vibecoding"],
            ["codex"]
        )
        self.assertEqual(merged_channels, ["vibecoding", "codex", "claude"])

    def test_select_channel_balanced_projects_should_keep_multi_channel_candidates(self):
        """通道化选择应覆盖多个通道候选项目"""
        self.fetcher.CHANNEL_TOP_N = 1
        all_projects = {
            "repo-vibe": {"name": "repo-vibe", "activity_score": 99, "matched_channels": ["vibecoding"]},
            "repo-codex": {"name": "repo-codex", "activity_score": 70, "matched_channels": ["codex"]},
            "repo-claude": {"name": "repo-claude", "activity_score": 65, "matched_channels": ["claude"]},
            "repo-vibe-2": {"name": "repo-vibe-2", "activity_score": 80, "matched_channels": ["vibecoding"]},
        }

        selected_projects = self.fetcher._select_channel_balanced_projects(all_projects, limit=3)
        selected_names = [project["name"] for project in selected_projects]

        self.assertIn("repo-vibe", selected_names)
        self.assertIn("repo-codex", selected_names)
        self.assertIn("repo-claude", selected_names)


if __name__ == "__main__":
    unittest.main()
