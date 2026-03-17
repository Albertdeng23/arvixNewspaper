import subprocess
import logging
import os
from pathlib import Path
from typing import List, Optional

from src.config_manager import config
from src.models import Paper, PaperStatus

logger = logging.getLogger(__name__)

class MarkerConverter:
    """封装 Marker-PDF 命令行工具，将 PDF 转换为高质量 Markdown"""

    def __init__(self):
        # 检查系统是否安装了 marker_single 脚本
        # Marker 安装后通常会提供 marker_single 命令
        self.marker_cmd = "marker_single" 
        self.output_root = config.paths.processed_md_dir
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _get_md_output_path(self, pdf_path: str) -> Path:
        """根据 PDF 路径计算预期的 Markdown 输出路径"""
        pdf_name = Path(pdf_path).stem
        # Marker 默认会在输出目录下创建一个以文件名命名的文件夹
        return self.output_root / pdf_name / f"{pdf_name}.md"

    def convert_one(self, paper: Paper) -> bool:
        """调用 Marker 转换单篇论文"""
        if not paper.pdf_path or not os.path.exists(paper.pdf_path):
            logger.error(f"PDF path not found for paper: {paper.metadata.arxiv_id}")
            return False

        pdf_path = Path(paper.pdf_path)
        # 执行命令: marker_single /path/to/file.pdf --output_dir /path/to/output --batch_multiplier 2
        # 注意：这里可以根据是否有 GPU 调整参数
        command = [
            self.marker_cmd,
            str(pdf_path),
            "--output_dir", str(self.output_root),
            "--batch_multiplier", "2", # 提高并行度
            "--max_pages", "30"        # 限制页数防止超长论文卡死
        ]

        logger.info(f"Starting Marker conversion for: {paper.metadata.arxiv_id}")
        
        try:
            # 使用 subprocess 运行命令行工具
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=300 # 单篇论文转换上限 5 分钟
            )
            
            expected_md = self._get_md_output_path(paper.pdf_path)
            
            if expected_md.exists():
                paper.md_path = str(expected_md)
                paper.status = PaperStatus.CONVERTED
                logger.info(f"Successfully converted to Markdown: {expected_md}")
                return True
            else:
                logger.error(f"Marker finished but MD file not found at {expected_md}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Marker conversion timed out for {paper.metadata.arxiv_id}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Marker failed with error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during conversion: {e}")
            return False

    def convert_batch(self, papers: List[Paper]) -> List[Paper]:
        """批量转换论文"""
        converted_papers = []
        for paper in papers:
            if self.convert_one(paper):
                converted_papers.append(paper)
        
        logger.info(f"Batch conversion complete. Success: {len(converted_papers)}/{len(papers)}")
        return converted_papers

# 简单测试逻辑
if __name__ == "__main__":
    # 模拟 Paper 对象进行测试
    pass
