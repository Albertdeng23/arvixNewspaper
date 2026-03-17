import datetime
import logging
from pathlib import Path
from typing import List, Optional

from openai import OpenAI
from src.config_manager import config
from src.models import Paper, DailyReport

logger = logging.getLogger(__name__)

class ReportGenerator:
    """负责将分析后的论文数据组装成最终的 Markdown 报纸排版"""

    def __init__(self):
        self.client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url
        )
        self.output_dir = config.paths.output_report_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_editorial(self, papers: List[Paper]) -> str:
        """让 LLM 根据今日所有论文的摘要和分析，生成一段 150 字的头版社论（趋势总结）"""
        logger.info("Generating daily editorial...")
        
        # 提取所有论文的核心信息供 LLM 参考
        summaries = []
        for p in papers:
            if p.analysis:
                summaries.append(f"- {p.metadata.title}: {p.analysis.one_sentence_summary}") # type: ignore
            else:
                summaries.append(f"- {p.metadata.title}: {p.metadata.abstract[:200]}...")
                
        prompt = f"""
你是一位资深的 AI 领域学术主编。请根据以下今日精选论文的核心创新点，撰写一段 150 字左右的【头版社论】。
要求：
1. 总结今日研究的整体趋势（例如：大家都在关注长上下文、多模态幻觉等）。
2. 语言风格专业、精炼、具有新闻感。
3. 直接输出社论正文，不要包含任何多余的问候语或格式。

今日论文概览：
{chr(10).join(summaries)}
"""
        try:
            response = self.client.chat.completions.create(
                model=config.llm.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5 # 稍微提高温度，让社论更有文采
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate editorial: {e}")
            return "今日 arXiv 抓取了多篇高质量论文，涵盖了多个前沿方向。以下是详细的深度解析。"

    def _build_markdown(self, report: DailyReport) -> str:
        """将 DailyReport 对象渲染为 Markdown 字符串"""
        date_str = report.date.strftime("%Y年%m月%d日")
        
        md = f"""# 🗞️ 【AI 科研早报】 (AI Research Daily)
**日期**：{date_str} ｜ **期数**：Vol. {report.issue_number} ｜ **领域**：{", ".join(config.arxiv.categories)}
*“消除信息差，洞悉大模型演进的每一天”*
***

## 🌍 头版社论：今日学术风向标 (Daily Trend)
> **主编（AI）导读**：
> {report.editorial}

***

## 🏆 头版头条：今日必读 (Lead Story)
"""
        # 渲染头条
        top = report.top_story
        md += f"### 📌 [{top.metadata.title}]({top.metadata.pdf_url})\n"
        md += f"**作者**：{', '.join(top.metadata.authors[:3])}{' et al.' if len(top.metadata.authors)>3 else ''} ｜ **机构**：arXiv\n\n"
        if top.analysis:
            md += f"**💡 核心简述**：{top.analysis.one_sentence_summary}\n\n"
            md += f"#### 🧠 元认知深度解码 (Metacognitive Analysis)\n"
            md += f"> **🎯 目的之问 (Purpose)**：\n> {top.analysis.purpose}\n>\n"
            md += f"> **🧱 本源之问 (Origin)**：\n> {top.analysis.origin}\n>\n"
            md += f"> **⚙️ 动力之问 (Dynamics)**：\n> {top.analysis.dynamics}\n>\n"
            md += f"> **🚧 边界之问 (Boundary)**：\n> {top.analysis.boundary}\n>\n"
            md += f"> **🚀 前沿之问 (Frontier)**：\n> {top.analysis.frontier}\n\n"
            md += f"**🔥 影响力评估**：{top.analysis.impact_score}/10\n"
        else:
            md += f"**摘要**：\n{top.metadata.abstract}\n"

        md += "\n***\n\n## 🔬 二版专栏：前沿深度解析 (Featured Research)\n\n"
        
        # 渲染深度解析
        for i, p in enumerate(report.featured_papers, 1):
            md += f"### {i}️⃣ [{p.metadata.title}]({p.metadata.pdf_url})\n"
            if p.analysis:
                md += f"**💡 核心简述**：{p.analysis.one_sentence_summary}\n\n"
                md += f"* **🎯 目的**：{p.analysis.purpose}\n"
                md += f"* **🧱 本源**：{p.analysis.origin}\n"
                md += f"* **🚧 边界**：{p.analysis.boundary}\n\n"
            else:
                md += f"* **摘要**：{p.metadata.abstract[:300]}...\n\n"

        md += "***\n\n## ⚡ 三版快讯：一句话速览 (Research in Brief)\n\n"
        
        # 渲染快讯
        for p in report.brief_news:
            tag = p.metadata.primary_category.split('.')[-1].upper() 
            md += f"* 🏷️ **[{tag}]** **[{p.metadata.title}]({p.metadata.pdf_url})**：\n"
            if p.analysis:
                md += f"  {p.analysis.one_sentence_summary}\n"
            else:
                md += f"  {p.metadata.abstract[:100]}...\n"

        md += "\n***\n*📢 **订阅说明**：本早报由 arXiv API + Marker + LLM 自动化流水线每日清晨生成。*\n"
        md += "*🤖 **免责声明**：AI 总结可能存在偏差，核心细节请参阅原论文。*\n"
        
        return md

    def generate(self, papers: List[Paper]) -> Optional[Path]:
        """主生成逻辑：排序、组装、渲染、保存"""
        if not papers:
            logger.warning("No papers provided to generate report.")
            return None

        logger.info(f"Generating report for {len(papers)} papers...")

        # 1. 按照影响力评分（impact_score）降序排序
        # 如果没有 analysis（比如降级处理的论文），默认给 0 分
        sorted_papers = sorted(
            papers, 
            key=lambda p: p.analysis.impact_score if p.analysis else 0, 
            reverse=True
        )

        # 2. 分配版面
        top_story = sorted_papers[0]
        # 假设取第 2-4 篇作为深度解析
        featured_papers = sorted_papers[1:4] if len(sorted_papers) > 1 else []
        # 剩下的作为快讯
        brief_news = sorted_papers[4:] if len(sorted_papers) > 4 else []

        # 3. 生成社论
        editorial = self._generate_editorial(sorted_papers)

        # 4. 构建 Report 对象
        # 这里简单用一年中的第几天作为期数
        issue_num = datetime.datetime.now().timetuple().tm_yday 
        
        report = DailyReport(
            date=datetime.date.today(),
            issue_number=issue_num,
            editorial=editorial,
            top_story=top_story,
            featured_papers=featured_papers,
            brief_news=brief_news
        )

        # 5. 渲染 Markdown
        md_content = self._build_markdown(report)

        # 6. 保存到文件
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        output_file = self.output_dir / f"AI_Daily_Report_{today_str}.md"
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(md_content)
            logger.info(f"Successfully generated daily report: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Failed to save report to {output_file}: {e}")
            return None

# 简单测试逻辑
if __name__ == "__main__":
    pass
