import os
import yaml
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 导入我们刚刚写的 PromptManager
from config.prompt_templates import PromptManager

# 显式加载 .env 文件
load_dotenv()

# ==========================================
# 数据模型定义 (映射 YAML 结构)
# ==========================================
class ProfileSettings(BaseModel):
    """单个领域画像的配置模型"""
    display_name: str
    arxiv_categories: List[str]
    report_title: str
    slogan: str

class GlobalSettings(BaseModel):
    """全局爬虫与分析设置"""
    max_results_per_day: int = 50
    top_n_selection: int = 10
    user_agent: str = "ArxivDailyBot/2.0"

# ==========================================
# 系统环境配置 (映射 .env 结构)
# ==========================================
class LLMSettings(BaseSettings):
    """大模型相关配置"""
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
    # 新增：YAML 配置文件的路径
    config_file: Path = base_dir / "config" / "settings.yaml"

    def create_dirs(self):
        """初始化必要的本地目录"""
        for path in [self.raw_pdf_dir, self.processed_md_dir, self.output_report_dir]:
            path.mkdir(parents=True, exist_ok=True)

# ==========================================
# 全局配置管理器 (AppConfig)
# ==========================================
class AppConfig:
    """全局总配置 (作为容器，动态管理当前激活的领域)"""
    def __init__(self):
        self.paths = PathSettings()
        self.llm = LLMSettings()
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        
        # 加载 YAML 配置
        self._load_yaml_config()
        
        # 动态状态：当前激活的画像和 PromptManager
        # 初始为 None，等待 main.py 启动时由用户选择并设置
        self.active_profile_name: str = None
        self.active_profile: ProfileSettings = None
        self.prompt_manager: PromptManager = None

    def _load_yaml_config(self):
        """解析 settings.yaml 文件"""
        if not self.paths.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.paths.config_file}")
            
        with open(self.paths.config_file, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
            
        # 将 YAML 中的 profiles 字典转换为 ProfileSettings 对象字典
        self.profiles: Dict[str, ProfileSettings] = {
            k: ProfileSettings(**v) for k, v in yaml_data.get('profiles', {}).items()
        }
        # 加载全局设置
        self.global_settings = GlobalSettings(**yaml_data.get('global_settings', {}))

    def set_active_profile(self, profile_name: str):
        """
        【核心方法】：动态切换当前激活的领域画像
        调用此方法后，整个系统的爬虫分类、提示词都会随之改变。
        """
        if profile_name not in self.profiles:
            raise ValueError(f"未找到名为 '{profile_name}' 的画像配置。请检查 settings.yaml。")
        
        self.active_profile_name = profile_name
        self.active_profile = self.profiles[profile_name]
        
        # 同步实例化对应的 PromptManager
        self.prompt_manager = PromptManager(profile_name)

# 实例化全局单例配置对象
config = AppConfig()

# 自动创建目录
config.paths.create_dirs()
