import re
import logging
from pathlib import Path
from typing import Optional

from src.models import Paper

logger = logging.getLogger(__name__)

class MarkdownCleaner:
    """针对学术论文 Markdown 的清洗工具，旨在减少 Token 消耗并提高 AI 分析质量"""

    def __init__(self):
        # 定义常见的“参考文献”标题正则（支持多种变体）
        self.ref_patterns = [
            re.compile(r'^#+\s*References?\s*$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^#+\s*Bibliography\s*$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^#+\s*参考文献\s*$', re.MULTILINE),
        ]
        # 定义“致谢”标题正则
        self.ack_patterns = [
            re.compile(r'^#+\s*Acknowledgements?\s*$', re.IGNORECASE | re.MULTILINE),
        ]

    def _truncate_at_references(self, content: str) -> str:
        """寻找参考文献的起始位置并切除之后的所有内容"""
        earliest_pos = len(content)
        found = False

        for pattern in self.ref_patterns:
            match = pattern.search(content)
            if match:
                # 记录最早出现的参考文献标志位
                if match.start() < earliest_pos:
                    earliest_pos = match.start()
                    found = True
        
        if found:
            logger.info(f"Truncated content at reference section (saved approx {len(content) - earliest_pos} chars).")
            return content[:earliest_pos]
        return content

    def _clean_whitespace(self, content: str) -> str:
        """清理多余的空行和空格，压缩文本"""
        # 将三个及以上的换行符替换为两个，保持段落感但压缩空间
        content = re.sub(r'\n{3,}', '\n\n', content)
        # 去除行尾空格
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
        return content.strip()

    def clean_paper(self, paper: Paper) -> Optional[str]:
        """
        读取 Paper 对象指向的 MD 文件，清洗后返回字符串。
        注意：我们不覆盖原始 MD 文件，只返回清洗后的文本供 LLM 使用。
        """
        if not paper.md_path or not Path(paper.md_path).exists():
            logger.warning(f"No Markdown file found to clean for {paper.metadata.arxiv_id}")
            return None

        try:
            with open(paper.md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. 切除参考文献
            content = self._truncate_at_references(content)
            
            # 2. 基础清洗
            content = self._clean_whitespace(content)
            
            # 3. (可选) 限制最大字符数，防止极端情况下的 Token 溢出
            # 假设 1 Token ≈ 4 字符，100k 字符约等于 25k Token
            max_chars = 100000 
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[Content Truncated due to length...]"

            return content

        except Exception as e:
            logger.error(f"Error cleaning Markdown for {paper.metadata.arxiv_id}: {e}")
            return None

# 简单测试逻辑
if __name__ == "__main__":
    # 测试正则匹配逻辑
    pass
