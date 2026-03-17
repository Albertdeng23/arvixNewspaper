import datetime
import logging
from typing import List

import arxiv
from src.config_manager import config
from src.models import Paper, PaperMetadata, PaperStatus

logger = logging.getLogger(__name__)

class ArxivClient:
    """封装 arXiv API 的交互逻辑"""

    def __init__(self):
        # 初始化 arxiv 客户端，配置频率限制和重试
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,  # 遵循 arXiv API 的频率限制建议
            num_retries=3
        )

    def _build_query(self) -> str:
        """
        构建查询字符串。
        从当前激活的领域画像中动态获取分类。
        """
        # 确保已经激活了某个领域
        if not config.active_profile:
            raise RuntimeError("在调用爬虫前，必须先通过 config.set_active_profile() 激活一个领域画像。")

        # 获取当前领域的分类列表
        categories = config.active_profile.arxiv_categories
        cat_query = " OR ".join([f"cat:{c}" for c in categories])
        
        query = f"({cat_query})"
        logger.info(f"Generated arXiv query for profile '{config.active_profile_name}': {query}")
        return query

    def fetch_today_papers(self) -> List[Paper]:
        """
        执行搜索并返回 Paper 对象列表
        """
        query_str = self._build_query()
        search = arxiv.Search(
            query=query_str,
            max_results=config.global_settings.max_results_per_day, # 从全局设置读取
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        papers = []
        try:
            for result in self.client.results(search):
                # 将 arxiv.Result 转换为我们的 PaperMetadata 模型
                metadata = PaperMetadata(
                    arxiv_id=result.get_short_id(),
                    title=result.title.replace("\n", " "), # 清理标题中的换行
                    authors=[author.name for author in result.authors],
                    abstract=result.summary.replace("\n", " "),
                    categories=result.categories,
                    primary_category=result.primary_category,
                    published_date=result.published.date(),
                    pdf_url=result.pdf_url,
                    comment=result.comment
                )
                
                # 封装进 Paper 对象，初始状态为 CRAWLED
                papers.append(Paper(metadata=metadata, status=PaperStatus.CRAWLED))
            
            logger.info(f"Successfully fetched {len(papers)} papers from arXiv.")
            return papers

        except Exception as e:
            logger.error(f"Error fetching papers from arXiv: {e}")
            return []

# 简单测试逻辑（仅当直接运行此文件时执行）
if __name__ == "__main__":
    pass
