"""
README 内容总结模块
负责从 GitHub 项目的 README 中提取或生成摘要
"""

import re
from typing import Optional


class ReadmeSummarizer:
    """README 内容总结器"""

    # 需要跳过的章节标题（通常不包含核心信息）
    SKIP_SECTIONS = [
        "Contributing",
        "License",
        "Authors",
        "Acknowledgments",
        "Changelog",
        "To Do",
        "TODO",
        "See Also",
        "References",
    ]

    def summarize(self, readme_content: str, max_length: int = 500) -> str:
        """
        总结 README 内容

        策略：
        1. 如果内容很短，直接返回
        2. 如果有明确的简介段落，提取它
        3. 否则提取前几段有意义的内容

        Args:
            readme_content: README 的 Markdown 内容
            max_length: 最大长度（字符数）

        Returns:
            摘要文本（保留 Markdown 代码块格式）
        """
        if not readme_content:
            return "暂无项目描述"

        # 清理内容（保留代码块）
        content = self._clean_content(readme_content)

        # 如果内容很短，直接返回
        if len(content) <= max_length:
            return content

        # 尝试找到简介段落
        intro = self._extract_intro(content)
        if intro:
            return self._truncate_to_length(intro, max_length)

        # 提取前几段
        paragraphs = self._extract_meaningful_paragraphs(content, max_paragraphs=3)
        summary = "\n\n".join(paragraphs)
        return self._truncate_to_length(summary, max_length)

    def is_meaningful_summary(self, summary: str) -> bool:
        """
        判断摘要是否有意义，过滤目录、分隔线等噪声内容
        """
        if not summary:
            return False

        text = summary.strip()
        if len(text) < 20:
            return False

        # 仅包含符号或分隔线的内容视为无效
        if re.fullmatch(r'[-_=*`#\s.]+', text):
            return False

        lowered = text.lower()
        noise_keywords = [
            "table of contents",
            "目录",
            "language",
            "license",
            "contributing",
        ]
        if any(keyword in lowered for keyword in noise_keywords) and len(text) < 60:
            return False

        return True

    def _clean_content(self, content: str) -> str:
        """
        清理 Markdown 内容，保留代码块
        """
        # 统一常见 HTML 空白实体
        content = content.replace("&nbsp;", " ")

        # 移除图片
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)

        # 保留短代码块（单行或3行以内），移除过长的代码块
        def keep_short_codeblocks(match):
            code = match.group(2)
            lines = code.split('\n')
            # 如果代码块很短（3行以内），保留它
            if len(lines) <= 3:
                return match.group(0)  # 保留原始代码块
            else:
                return ''  # 移除长代码块

        content = re.sub(
            r'```(\w*)\n(.*?)```',
            keep_short_codeblocks,
            content,
            flags=re.DOTALL
        )

        # 保留行内代码（不处理）
        # 处理空链接，避免渲染成无意义 [](...)
        content = re.sub(r'\[\s*\]\((https?://[^)]+)\)', r'\1', content)
        # 保留链接文本和 URL 信息，避免信息丢失
        content = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1 (\2)', content)
        # 移除 HTML 标签
        content = re.sub(r'<[^>]+>', '', content)
        # 清理多余空格
        content = re.sub(r'[ \t]+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    def _extract_intro(self, content: str) -> Optional[str]:
        """
        提取简介段落

        查找模式：
        - 第一个段落
        - 或在 "## About"、"## Introduction" 等标题下的段落
        """
        lines = content.split("\n")
        intro_lines = []
        found_intro_section = False

        for i, line in enumerate(lines):
            line = line.strip()

            # 检查是否是简介章节标题
            if line.startswith("## ") and any(
                keyword in line.lower()
                for keyword in ["about", "introduction", "overview", "what is"]
            ):
                found_intro_section = True
                continue

            # 如果找到了简介章节，开始收集内容
            if found_intro_section:
                if line.startswith("## "):
                    # 遇到下一个章节，停止
                    break
                if line:
                    intro_lines.append(line)
                if len(intro_lines) >= 5:  # 最多取5行
                    break
            elif i == 0 or (i > 0 and not line.startswith("#")):
                # 第一个非标题段落
                if line and not line.startswith("#"):
                    intro_lines.append(line)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not next_line.startswith("#"):
                            intro_lines.append(next_line)
                    break

        if intro_lines:
            return " ".join(intro_lines)

        return None

    def _extract_meaningful_paragraphs(
        self, content: str, max_paragraphs: int = 3
    ) -> list:
        """提取有意义的段落"""
        lines = content.split("\n")
        paragraphs = []
        current_paragraph = []

        for line in lines:
            line = line.strip()

            # 跳过章节标题
            if line.startswith("## ") and any(
                skip in line for skip in self.SKIP_SECTIONS
            ):
                continue

            # 遇到新章节
            if line.startswith("## "):
                if current_paragraph:
                    paragraph = " ".join(current_paragraph).strip()
                    if paragraph and len(paragraph) > 20:  # 忽略太短的段落
                        paragraphs.append(paragraph)
                        if len(paragraphs) >= max_paragraphs:
                            break
                current_paragraph = []
                continue

            # 收集段落内容
            if line:
                current_paragraph.append(line)
            elif current_paragraph:
                # 空行表示段落结束
                paragraph = " ".join(current_paragraph).strip()
                if paragraph and len(paragraph) > 20:
                    paragraphs.append(paragraph)
                    if len(paragraphs) >= max_paragraphs:
                        break
                current_paragraph = []

        # 处理最后一个段落
        if current_paragraph:
            paragraph = " ".join(current_paragraph).strip()
            if paragraph and len(paragraph) > 20:
                paragraphs.append(paragraph)

        return paragraphs

    def _truncate_to_length(self, text: str, max_length: int) -> str:
        """将文本截断到指定长度"""
        if len(text) <= max_length:
            return text

        # 在接近 max_length 的空格处截断
        truncated = text[: max_length - 3]
        last_space = truncated.rfind(" ")
        if last_space > max_length // 2:  # 确保不会截断太多
            truncated = truncated[:last_space]

        return truncated + "..."


def generate_summary_with_ai(readme_content: str, api_key: str) -> str:
    """
    使用 AI API 生成摘要（可选功能）

    如果需要更高质量的摘要，可以调用 OpenAI/Claude API

    Args:
        readme_content: README 内容
        api_key: AI API 密钥

    Returns:
        AI 生成的摘要
    """
    # 这是一个预留接口，可以根据需要实现
    # 目前使用本地摘要方法
    summarizer = ReadmeSummarizer()
    return summarizer.summarize(readme_content)
