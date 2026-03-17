import logging
import sys
import time
from pathlib import Path

# 导入我们编写的所有模块
from src.config_manager import config
from src.crawler.arxiv_client import ArxivClient
from src.analyzer.paper_ranker import PaperRanker
from src.crawler.downloader import PaperDownloader
from src.converter.marker_wrapper import MarkerConverter
from src.analyzer.summarizer import PaperSummarizer
from src.generator.layout_engine import ReportGenerator

# 配置全局日志格式
logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.paths.data_dir / "pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("MainPipeline")

def run_daily_pipeline():
    """执行每日科研早报生成流水线"""
    start_time = time.time()
    logger.info("=== Starting AI Research Daily Pipeline ===")
    logger.info(f"Target Categories: {config.arxiv.categories}")
    logger.info(f"LLM Model: {config.llm.model_name}")

    # ---------------------------------------------------------
    # 阶段 1: 数据获取 (Fetch Metadata)
    # ---------------------------------------------------------
    logger.info("\n--- Phase 1: Fetching Metadata ---")
    crawler = ArxivClient()
    all_papers = crawler.fetch_today_papers()
    
    if not all_papers:
        logger.error("No papers fetched today. Pipeline aborted.")
        return

    # ---------------------------------------------------------
    # 阶段 2: 智能初筛 (Rank & Select)
    # ---------------------------------------------------------
    logger.info("\n--- Phase 2: AI Ranking & Selection ---")
    ranker = PaperRanker()
    selected_papers = ranker.rank_and_select(all_papers)
    
    if not selected_papers:
        logger.error("AI selection failed or returned empty. Pipeline aborted.")
        return

    # ---------------------------------------------------------
    # 阶段 3: 物理下载 (Download PDFs)
    # ---------------------------------------------------------
    logger.info("\n--- Phase 3: Downloading PDFs ---")
    downloader = PaperDownloader()
    downloaded_papers = downloader.download_batch(selected_papers)
    
    if not downloaded_papers:
        logger.error("All PDF downloads failed. Pipeline aborted.")
        return

    # ---------------------------------------------------------
    # 阶段 4: 格式转换 (PDF to Markdown via Marker)
    # ---------------------------------------------------------
    logger.info("\n--- Phase 4: Converting PDFs to Markdown ---")
    converter = MarkerConverter()
    converted_papers = converter.convert_batch(downloaded_papers)
    
    if not converted_papers:
        logger.warning("All Marker conversions failed. Proceeding with abstracts only.")
        # 即使转换失败，我们依然可以基于摘要生成早报（降级处理）
        papers_to_analyze = downloaded_papers 
    else:
        papers_to_analyze = converted_papers

    # ---------------------------------------------------------
    # 阶段 5: 深度分析 (LLM Summarization)
    # ---------------------------------------------------------
    logger.info("\n--- Phase 5: Deep AI Analysis ---")
    summarizer = PaperSummarizer()
    # 注意：这里会内部调用 MarkdownCleaner 进行文本清洗
    analyzed_papers = summarizer.analyze_batch(papers_to_analyze)
    
    # 即使部分分析失败，我们依然把所有进入此阶段的论文传给生成器
    # 生成器内部有容错逻辑（if p.analysis: ... else: ...）

    # ---------------------------------------------------------
    # 阶段 6: 排版生成 (Generate Daily Report)
    # ---------------------------------------------------------
    logger.info("\n--- Phase 6: Generating Report ---")
    generator = ReportGenerator()
    report_path = generator.generate(papers_to_analyze)

    # ---------------------------------------------------------
    # 总结与收尾
    # ---------------------------------------------------------
    elapsed_time = time.time() - start_time
    logger.info("\n=== Pipeline Completed Successfully ===")
    logger.info(f"Total time elapsed: {elapsed_time:.2f} seconds")
    if report_path:
        logger.info(f"🎉 Your Daily Report is ready at: {report_path}")
    else:
        logger.error("Failed to generate the final report file.")

if __name__ == "__main__":
    try:
        run_daily_pipeline()
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Pipeline crashed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)
