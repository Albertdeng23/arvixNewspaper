import json
import logging
from typing import List

from openai import OpenAI
from src.config_manager import config
from src.models import Paper

logger = logging.getLogger(__name__)

class PaperRanker:
    """利用 LLM 对论文摘要进行初筛和打分"""

    def __init__(self):
        self.client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url
        )

    def _generate_rank_prompt(self, papers: List[Paper]) -> str:
        """构建用于打分的 Prompt (动态获取)"""
        paper_list_str = ""
        for i, p in enumerate(papers):
            paper_list_str += f"ID: {i}\nTitle: {p.metadata.title}\nAbstract: {p.metadata.abstract}\n---\n"

        # 从 PromptManager 动态获取当前领域的初筛 Prompt
        top_n = config.global_settings.top_n_selection
        return config.prompt_manager.get_ranker_prompt(paper_list_str, top_n)

    def rank_and_select(self, papers: List[Paper]) -> List[Paper]:
        """
        调用 LLM 进行筛选，返回被选中的 Paper 对象列表
        """
        if not papers:
            return []
        
        top_n = config.global_settings.top_n_selection
        if len(papers) <= top_n:
            logger.info("Paper count is less than selection limit, skipping ranking.")
            return papers

        logger.info(f"Ranking {len(papers)} papers using LLM...")
        
        try:
            response = self.client.chat.completions.create(
                model=config.llm.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的学术筛选助手，只输出 JSON。"},
                    {"role": "user", "content": self._generate_rank_prompt(papers)}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            
            # 清理 AI 可能带有的 Markdown 代码块标记
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            selected_data = json.loads(content)
            
            # 鲁棒性提取
            if isinstance(selected_data, dict):
                for key, value in selected_data.items():
                    if isinstance(value, list):
                        selected_data = value
                        break
                else:
                    selected_data = [selected_data]
            
            selected_papers = []
            if isinstance(selected_data, list):
                for item in selected_data:
                    if isinstance(item, dict):
                        idx = item.get("id")
                        if isinstance(idx, int) and 0 <= idx < len(papers):
                            selected_papers.append(papers[idx])
            
            logger.info(f"LLM selected {len(selected_papers)} high-quality papers.")
            return selected_papers if selected_papers else papers[:top_n]

        except Exception as e:
            logger.error(f"Error during paper ranking: {e}")
            return papers[:top_n]
