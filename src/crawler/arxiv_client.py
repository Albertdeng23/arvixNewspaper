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
        例如: (cat:cs.AI OR cat:cs.CL) AND submittedDate:[202403160000 TO 202403170000]
        """
        # 获取分类部分
        cat_query = " OR ".join([f"cat:{c}" for c in config.arxiv.categories])
        query = f"({cat_query})"
        logger.info(f"Generated arXiv query: {query}")
        return query

    def fetch_today_papers(self) -> List[Paper]:
        """
        执行搜索并返回 Paper 对象列表
        """
        query_str = self._build_query()
        search = arxiv.Search(
            query=query_str,
            max_results=config.arxiv.max_results_per_day,
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
                    pdf_url=result.pdf_url, # type: ignore
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
    logging.basicConfig(level=logging.INFO)
    client = ArxivClient()
    results = client.fetch_today_papers()
    for p in results[:3]:
        print(f"[{p.metadata.arxiv_id}] {p.metadata.title}")
