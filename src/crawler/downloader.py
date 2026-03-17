import time
import random
import logging
from pathlib import Path
from typing import List
import httpx
from src.config_manager import config
from src.models import Paper, PaperStatus

logger = logging.getLogger(__name__)

class PaperDownloader:
    """负责从 arXiv 下载 PDF 文件并管理本地存储"""

    def __init__(self):
        # 伪装成真实的浏览器，并添加 Referer 绕过部分防盗链
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/pdf",
            "Referer": "https://arxiv.org/"
        }
        config.paths.raw_pdf_dir.mkdir(parents=True, exist_ok=True)

    def _get_local_path(self, arxiv_id: str) -> Path:
        """生成本地存储路径"""
        today_str = time.strftime("%Y-%m-%d")
        date_dir = config.paths.raw_pdf_dir / today_str
        date_dir.mkdir(parents=True, exist_ok=True)
        safe_id = arxiv_id.replace("/", "_")
        return date_dir / f"{safe_id}.pdf"

    def download_one(self, paper: Paper) -> bool:
        """下载单篇论文"""
        local_path = self._get_local_path(paper.metadata.arxiv_id)
        
        if local_path.exists() and local_path.stat().st_size > 1000:
            logger.info(f"Paper {paper.metadata.arxiv_id} already exists, skipping.")
            paper.pdf_path = str(local_path)
            paper.status = PaperStatus.DOWNLOADED
            return True

        logger.info(f"Downloading PDF: {paper.metadata.title[:50]}...")
        
        # 核心修复：提取纯净的 ID（去掉 v1, v2 等版本号）
        # 例如 2603.15619v1 -> 2603.15619
        base_id = paper.metadata.arxiv_id.split('v')[0]
        
        # 准备多个下载源进行尝试
        urls_to_try = [
            f"https://arxiv.org/pdf/{base_id}.pdf",         # 官方标准路径
            f"https://export.arxiv.org/pdf/{base_id}.pdf"   # 官方导出节点
        ]
        
        for download_url in urls_to_try:
            try:
                with httpx.Client(headers=self.headers, follow_redirects=True, timeout=60.0) as client:
                    response = client.get(download_url)
                    
                    if response.status_code == 200:
                        # 终极校验：检查下载下来的文件是不是真的 PDF
                        # PDF 文件的二进制头部必须包含 b"%PDF"
                        if b"%PDF" in response.content[:10]:
                            with open(local_path, "wb") as f:
                                f.write(response.content)
                            
                            paper.pdf_path = str(local_path)
                            paper.status = PaperStatus.DOWNLOADED
                            logger.info(f"Successfully downloaded to {local_path}")
                            
                            # 成功后随机休眠，保护 IP
                            time.sleep(random.uniform(2.0, 5.0))
                            return True
                        else:
                            logger.warning(f"Downloaded content is not a valid PDF from {download_url} (Might be a captcha page).")
                    else:
                        logger.warning(f"Failed with status {response.status_code} from {download_url}")
            
            except Exception as e:
                logger.warning(f"Error fetching from {download_url}: {e}")
        
        # 如果所有 URL 都失败了
        error_msg = f"All download attempts failed for {paper.metadata.arxiv_id}"
        logger.error(error_msg)
        paper.status = PaperStatus.FAILED
        paper.error_message = error_msg
        return False

    def download_batch(self, papers: List[Paper]) -> List[Paper]:
        """批量下载论文列表"""
        successful_papers = []
        for paper in papers:
            if self.download_one(paper):
                successful_papers.append(paper)
        
        logger.info(f"Batch download complete. Success: {len(successful_papers)}/{len(papers)}")
        return successful_papers
