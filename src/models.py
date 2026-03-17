import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class PaperStatus(Enum):
    """定义论文在流水线中的处理状态"""
    CRAWLED = "crawled"      # 已抓取元数据
    DOWNLOADED = "downloaded" # PDF已下载
    CONVERTED = "converted"   # 已转为 Markdown
    ANALYZED = "analyzed"     # AI已完成单篇分析
    FAILED = "failed"         # 处理失败

class PaperMetadata(BaseModel):
    """从 arXiv 抓取的原始元数据"""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    primary_category: str
    published_date: datetime.date
    pdf_url: HttpUrl
    comment: Optional[str] = None

class PaperAnalysis(BaseModel):
    """AI 对单篇论文的深度分析结果"""
    core_innovation: str = Field(..., description="核心创新点")
    problem_solved: str = Field(..., description="解决的具体问题")
    methodology: List[str] = Field(..., description="关键方法论步骤")
    key_conclusions: str = Field(..., description="关键结论")
    impact_score: int = Field(..., ge=1, le=10, description="影响力评分 1-10")
    why_it_matters: str = Field(..., description="为什么值得关注")

class Paper(BaseModel):
    """贯穿整个流程的核心论文对象"""
    metadata: PaperMetadata
    status: PaperStatus = PaperStatus.CRAWLED
    
    # 路径信息
    pdf_path: Optional[str] = None
    md_path: Optional[str] = None
    
    # 分析结果
    analysis: Optional[PaperAnalysis] = None
    
    # 错误记录
    error_message: Optional[str] = None

class DailyReport(BaseModel):
    """最终生成的早报结构化数据"""
    date: datetime.date
    issue_number: int
    editorial: str = Field(..., description="今日学术风向标/社论")
    top_story: Paper = Field(..., description="今日头版头条论文")
    featured_papers: List[Paper] = Field(..., description="二版深度解析论文")
    brief_news: List[Paper] = Field(..., description="三版一句话快讯")
    
    def to_markdown(self) -> str:
        """
        预留方法：将对象转换为最终的报纸排版字符串
        后续由 src/generator/layout_engine.py 实现具体逻辑
        """
        pass

class PaperAnalysis(BaseModel):
    """AI 对单篇论文的【元认知】深度分析结果"""
    one_sentence_summary: str = Field(..., description="一句话高度概括论文核心贡献")
    
    # 元认知五个维度
    purpose: str = Field(..., description="目的之问：解决什么核心痛点或终极目标")
    origin: str = Field(..., description="本源之问：拆无可拆的底层实体/数学对象/核心假设是什么")
    dynamics: str = Field(..., description="动力之问：这些底层基石是如何互动的（核心机制/算法流）")
    boundary: str = Field(..., description="边界之问：这个体系什么时候会失效、面临什么瓶颈或局限性")
    frontier: str = Field(..., description="前沿之问：这项研究为未来指明了什么方向，下一步该做什么")
    
    impact_score: int = Field(..., ge=1, le=10, description="影响力评分 1-10")
