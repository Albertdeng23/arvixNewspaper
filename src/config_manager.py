import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 显式加载 .env 文件到系统环境变量中
# 这样 Pydantic 无论在哪一层都能直接读到配置
load_dotenv()

class ArxivSettings(BaseSettings):
    """arXiv 相关配置"""
    categories: List[str] = ["cs.AI", "cs.CL", "cs.LG"]
    max_results_per_day: int = 50
    top_n_selection: int = 10
    user_agent: str = "ArxivDailyBot/1.0"

class LLMSettings(BaseSettings):
    """大模型相关配置"""
    # 使用 alias 自动绑定环境变量
    api_key: str = Field(default=..., alias="LLM_API_KEY")
    base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    model_name: str = Field(default="gpt-4o-mini", alias="MODEL_NAME")
    temperature: float = 0.3
    max_tokens: int = 2000

class PathSettings(BaseSettings):
    """路径相关配置"""
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    raw_pdf_dir: Path = data_dir / "raw_pdf"
    processed_md_dir: Path = data_dir / "processed_md"
    output_report_dir: Path = data_dir / "reports"

    def create_dirs(self):
        """初始化必要的本地目录"""
        for path in [self.raw_pdf_dir, self.processed_md_dir, self.output_report_dir]:
            path.mkdir(parents=True, exist_ok=True)

class AppConfig:
    """全局总配置 (作为容器，不再继承 BaseSettings)"""
    def __init__(self):
        self.arxiv = ArxivSettings()
        self.llm = LLMSettings()
        self.paths = PathSettings()
        self.debug = os.getenv("DEBUG", "False").lower() == "true"

# 实例化全局配置对象
config = AppConfig()

# 自动创建目录
config.paths.create_dirs()
