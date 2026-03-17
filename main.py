import logging
import sys
import time
from pathlib import Path

# 导入配置管理器
from src.config_manager import config

# 导入流水线模块
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

def interactive_menu() -> str:
    """
    显示交互式菜单，让用户选择要生成的早报领域。
    返回选中的 profile_name (如 'ai', 'materials')
    """
    print("\n" + "="*50)
    print(" 🗞️ 欢迎使用 arXiv 多领域科研早报系统")
    print("="*50)
    print("请选择您今天想生成的早报领域：\n")
    
    # 从配置中动态读取所有可用的画像
    profiles = list(config.profiles.keys())
    for i, profile_key in enumerate(profiles, 1):
        profile_data = config.profiles[profile_key]
        print(f"  [{i}] {profile_data.display_name}")
        print(f"      (分类: {', '.join(profile_data.arxiv_categories)})")
    
    print("\n  [0] 退出程序")
    print("-" * 50)
    
    while True:
        try:
            choice = input("请输入编号并按回车: ").strip()
            if choice == '0':
                print("👋 感谢使用，再见！")
                sys.exit(0)
                
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(profiles):
                selected_profile = profiles[choice_idx]
                print(f"\n✅ 已选择: {config.profiles[selected_profile].display_name}")
                return selected_profile
            else:
                print("❌ 无效的编号，请重新输入。")
        except ValueError:
            print("❌ 请输入有效的数字。")
        except KeyboardInterrupt:
            print("\n👋 感谢使用，再见！")
            sys.exit(0)

def run_daily_pipeline():
    """执行每日科研早报生成流水线"""
    start_time = time.time()
    
    # 打印当前激活的配置信息
    logger.info("=== Starting Research Daily Pipeline ===")
    logger.info(f"Active Profile: {config.active_profile.display_name}")
    logger.info(f"Target Categories: {config.active_profile.arxiv_categories}")
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
    if config.use_marker_pdf:
        logger.info("\n--- Phase 4: Converting PDFs to Markdown ---")
        converter = MarkerConverter()
        converted_papers = converter.convert_batch(downloaded_papers)
        
        if not converted_papers:
            logger.warning("All Marker conversions failed. Proceeding with abstracts only.")
            papers_to_analyze = downloaded_papers 
        else:
            papers_to_analyze = converted_papers
    else:
        logger.info("\n--- Phase 4: Skipped (USE_MARKER_PDF=False). Using abstracts only. ---")
        # 直接将下载好的论文传给下一阶段，分析器会自动降级使用摘要
        papers_to_analyze = downloaded_papers

    # ---------------------------------------------------------
    # 阶段 5: 深度分析 (LLM Summarization)
    # ---------------------------------------------------------
    logger.info("\n--- Phase 5: Deep AI Analysis ---")
    summarizer = PaperSummarizer()
    analyzed_papers = summarizer.analyze_batch(papers_to_analyze)

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
        # 1. 启动交互式菜单，获取用户选择
        selected_profile_name = interactive_menu()
        
        # 2. 将用户选择注入到全局配置管理器中
        config.set_active_profile(selected_profile_name)
        
        # 3. 启动流水线
        run_daily_pipeline()
        
    except Exception as e:
        logger.critical(f"Pipeline crashed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)
