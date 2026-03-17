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
        # 初始化 LLM 客户端（适配 OpenAI 格式的 API）
        self.client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url
        )

    def _generate_rank_prompt(self, papers: List[Paper]) -> str:
        """构建用于打分的 Prompt"""
        paper_list_str = ""
        for i, p in enumerate(papers):
            paper_list_str += f"ID: {i}\nTitle: {p.metadata.title}\nAbstract: {p.metadata.abstract}\n---\n"

        prompt = f"""
你是一位资深的 AI 研究员。请阅读以下 {len(papers)} 篇论文的标题和摘要。
你的任务是从中挑选出最具有【创新性】、【工程落地价值】或【行业影响力】的 {config.arxiv.top_n_selection} 篇论文。

请直接返回一个 JSON 数组，包含挑选出的论文 ID 和简短的推荐理由。格式如下：
[
    {{"id": 0, "reason": "提出了全新的注意力机制，大幅降低显存占用"}},
    {{"id": 5, "reason": "在大模型幻觉抑制方面有突破性进展"}}
]

待评价论文列表：
{paper_list_str}
"""
        return prompt

    def rank_and_select(self, papers: List[Paper]) -> List[Paper]:
        """
        调用 LLM 进行筛选，返回被选中的 Paper 对象列表
        """
        if not papers:
            return []
        
        if len(papers) <= config.arxiv.top_n_selection:
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
            
            content = response.choices[0].message.content.strip() # type: ignore
            
            # 清理 AI 可能带有的 Markdown 代码块标记 (```json ... ```)
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            selected_data = json.loads(content)
            
            # 鲁棒性提取：如果 AI 返回的是字典，寻找里面的列表
            if isinstance(selected_data, dict):
                for key, value in selected_data.items():
                    if isinstance(value, list):
                        selected_data = value
                        break
                else:
                    # 如果字典里没有列表，强行包装成列表
                    selected_data = [selected_data]
            
            selected_papers = []
            # 确保 selected_data 现在是一个列表
            if isinstance(selected_data, list):
                for item in selected_data:
                    if isinstance(item, dict): # 确保 item 是字典
                        idx = item.get("id")
                        # 确保 idx 是整数且在合法范围内
                        if isinstance(idx, int) and 0 <= idx < len(papers):
                            selected_papers.append(papers[idx])
            
            logger.info(f"LLM selected {len(selected_papers)} high-quality papers.")
            return selected_papers if selected_papers else papers[:config.arxiv.top_n_selection]

        except Exception as e:
            logger.error(f"Error during paper ranking: {e}")
            return papers[:config.arxiv.top_n_selection]

# 简单测试逻辑
if __name__ == "__main__":
    # 假设已有 papers 列表...
    pass
