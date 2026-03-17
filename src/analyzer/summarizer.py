import json
import logging
from typing import List

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
        """构建深度分析 Prompt (动态获取)"""
        max_input_chars = 120000
        if len(content) > max_input_chars:
            content = content[:max_input_chars] + "\n\n[...Truncated...]"

        # 从 PromptManager 动态获取当前领域的深度分析 Prompt
        return config.prompt_manager.get_summary_prompt(content)

    def analyze_paper(self, paper: Paper) -> bool:
        """
        对单篇论文进行分析，结果存入 paper.analysis
        """
        content = self.cleaner.clean_paper(paper)
        
        if not content:
            logger.warning(f"No full text for {paper.metadata.arxiv_id}. Using abstract for analysis.")
            content = f"【注意：由于PDF全文提取失败，请仅基于以下论文标题和摘要进行逻辑推演和分析】\n标题：{paper.metadata.title}\n摘要：{paper.metadata.abstract}"

        logger.info(f"Analyzing paper: {paper.metadata.title[:50]}...")

        try:
            response = self.client.chat.completions.create(
                model=config.llm.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的学术分析助手，只输出 JSON。"},
                    {"role": "user", "content": self._generate_analysis_prompt(content)}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result_json = json.loads(response.choices[0].message.content)
            
            analysis = PaperAnalysis(**result_json)
            paper.analysis = analysis
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
