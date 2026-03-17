import json
import logging
from typing import List, Optional

from openai import OpenAI
from src.config_manager import config
from src.models import Paper, PaperAnalysis, PaperStatus
from src.converter.md_cleaner import MarkdownCleaner

logger = logging.getLogger(__name__)

class PaperSummarizer:
    """利用 LLM 对单篇论文进行深度分析"""

    def __init__(self):
        self.client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url
        )
        self.cleaner = MarkdownCleaner()
    def _generate_analysis_prompt(self, content: str) -> str:
        """构建基于【元认知】框架的深度分析 Prompt"""
        max_input_chars = 120000
        if len(content) > max_input_chars:
            content = content[:max_input_chars] + "\n\n[...Truncated...]"

        prompt = f"""
你是一位顶级的 AI 领域战略分析师和学术哲学家。请阅读以下论文内容，并使用【元认知】框架对其进行深度解构。
你的目标是透过现象看本质，为《科研早报》撰写一份极具洞察力的深度解析。

请严格按照以下 JSON 格式输出（不要输出任何 Markdown 代码块标记，只输出纯 JSON）：
{{
    "one_sentence_summary": "用一句话概括其核心技术贡献",
    "purpose": "【目的之问】：这篇论文究竟想解决什么核心痛点？它的终极目标是什么？",
    "origin": "【本源之问】：剥开表象，这项研究拆无可拆的底层实体、核心数学对象或最基础的假设是什么？（例如：将文本视为图、将注意力视为路由等）",
    "dynamics": "【动力之问】：这些底层基石是如何互动的？请解释其核心运转机制或算法流。",
    "boundary": "【边界之问】：批判性思考——这个体系在什么极端情况下会失效？它面临的物理、算力或理论瓶颈是什么？",
    "frontier": "【前沿之问】：这项研究打破了什么旧有认知？为未来的 AI 发展指明了什么具体方向？",
    "impact_score": 8
}}

论文内容：
{content}
"""
        return prompt
    def analyze_paper(self, paper: Paper) -> bool:
        """
        对单篇论文进行分析，结果存入 paper.analysis
        """
        # 1. 获取清洗后的文本
        content = self.cleaner.clean_paper(paper)
        if not content:
            logger.error(f"Skipping analysis for {paper.metadata.arxiv_id}: No content available.")
            return False

        logger.info(f"Analyzing paper: {paper.metadata.title[:50]}...")

        try:
            response = self.client.chat.completions.create(
                model=config.llm.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的学术分析助手，只输出 JSON。"},
                    {"role": "user", "content": self._generate_analysis_prompt(content)}
                ],
                response_format={"type": "json_object"},
                temperature=0.2 # 降低随机性，保证事实准确
            )

            # 2. 解析 JSON
            result_json = json.loads(response.choices[0].message.content) # type: ignore
            
            # 3. 填充 PaperAnalysis 模型
            analysis = PaperAnalysis(**result_json)
            paper.analysis = analysis # type: ignore
            paper.status = PaperStatus.ANALYZED
                
            logger.info(f"Analysis complete for {paper.metadata.arxiv_id}. Impact Score: {analysis.impact_score}")
            return True

        except json.JSONDecodeError:
            logger.error(f"LLM returned invalid JSON for {paper.metadata.arxiv_id}")
            return False
        except Exception as e:
            logger.error(f"Error analyzing paper {paper.metadata.arxiv_id}: {e}")
            return False

    def analyze_batch(self, papers: List[Paper]) -> List[Paper]:
        """批量分析论文"""
        analyzed_papers = []
        for paper in papers:
            if self.analyze_paper(paper):
                analyzed_papers.append(paper)
        
        logger.info(f"Batch analysis complete. Success: {len(analyzed_papers)}/{len(papers)}")
        return analyzed_papers

# 简单测试逻辑
if __name__ == "__main__":
    # 模拟 Paper 对象进行测试
    pass
