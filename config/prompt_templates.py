from typing import Dict

# ==========================================
# 1. 通用 JSON 输出格式定义 (所有领域共用)
# ==========================================
METACOGNITION_JSON_FORMAT = """
请严格按照以下 JSON 格式输出（不要输出任何 Markdown 代码块标记，只输出纯 JSON）：
{
    "one_sentence_summary": "用一句话概括其核心贡献或发现",
    "purpose": "【目的之问】：这篇论文究竟想解决什么核心痛点？它的终极目标是什么？",
    "origin": "【本源之问】：剥开表象，这项研究拆无可拆的底层实体、核心数学对象或最基础的假设是什么？",
    "dynamics": "【动力之问】：这些底层基石是如何互动的？请解释其核心运转机制或演化过程。",
    "boundary": "【边界之问】：批判性思考——这个体系在什么极端情况下会失效？它面临的物理、算力、成本或理论瓶颈是什么？",
    "frontier": "【前沿之问】：这项研究打破了什么旧有认知？为未来的发展指明了什么具体方向？",
    "impact_score": 8
}
"""

# ==========================================
# 2. 领域提示词插件注册表 (Plugin Registry)
# ==========================================
PROMPT_REGISTRY: Dict[str, Dict[str, str]] = {
    
    # --------------------------------------
    # [插件 1] 人工智能 (AI)
    # --------------------------------------
    "ai": {
        "ranker_system": "你是一位顶尖的 AI 领域战略分析师。",
        "ranker_criteria": "【算法创新】、【工程落地价值】或【大模型前沿探索】",
        "summary_system": "你是一位顶级的 AI 领域战略分析师和学术哲学家。请使用【元认知】框架对论文进行深度解构。",
        "summary_hints": "在分析本源和动力时，请关注：注意力机制、参数空间、数据流、算力分配等 AI 核心概念。",
        "editorial_system": "你是一位资深的 AI 领域学术主编。",
        "editorial_hints": "总结今日趋势时，可关注：长上下文、多模态幻觉、Agent 协作、推理效率等。"
    },

    # --------------------------------------
    # [插件 2] 材料科学 (Materials Science)
    # --------------------------------------
    "materials": {
        "ranker_system": "你是一位顶尖的材料科学与工程领域科学家。",
        "ranker_criteria": "【材料性能突破】、【合成工艺创新】或【底层微观机理揭示】",
        "summary_system": "你是一位顶级的材料科学战略分析师。请使用【元认知】框架对论文进行深度解构。",
        "summary_hints": "在分析本源和动力时，请关注：晶体结构、化学键演变、电子态密度(DOS)、热力学相变、缺陷迁移等材料学核心概念。",
        "editorial_system": "你是一位资深的材料科学领域学术主编。",
        "editorial_hints": "总结今日趋势时，可关注：固态电池、钙钛矿稳定性、高熵合金、AI 计算材料学(AI4Science)等。"
    },

    # --------------------------------------
    # [插件 3] 理论物理 (Physics)
    # --------------------------------------
    "physics": {
        "ranker_system": "你是一位诺贝尔奖级别的理论与实验物理学家。",
        "ranker_criteria": "【理论模型突破】、【实验观测新发现】或【对现有物理定律的挑战】",
        "summary_system": "你是一位顶级的物理学战略分析师。请使用【元认知】框架对论文进行深度解构。",
        "summary_hints": "在分析本源和动力时，请关注：量子态、时空几何、对称性破缺、相互作用场、守恒定律等物理学核心概念。",
        "editorial_system": "你是一位资深的物理学顶级期刊主编。",
        "editorial_hints": "总结今日趋势时，可关注：量子计算、凝聚态拓扑、暗物质探测、弦理论进展等。"
    },

    # --------------------------------------
    # [插件 4] 现代数学 (Mathematics)
    # --------------------------------------
    "math": {
        "ranker_system": "你是一位菲尔兹奖级别的数学家。",
        "ranker_criteria": "【核心猜想证明】、【新数学结构的提出】或【跨分支的深刻联系】",
        "summary_system": "你是一位顶级的数学哲学家。请使用【元认知】框架对论文进行深度解构。",
        "summary_hints": "在分析本源和动力时，请关注：公理体系、代数结构、拓扑不变量、流形演化、逻辑推演链条等纯数学概念。",
        "editorial_system": "你是一位资深的数学四大刊主编。",
        "editorial_hints": "总结今日趋势时，可关注：朗兰兹纲领、代数几何新进展、偏微分方程的解、数论突破等。"
    }
}

# ==========================================
# 3. 提示词生成工厂 (Prompt Factory)
# ==========================================
class PromptManager:
    """根据当前激活的领域，动态生成对应的 Prompt"""
    
    def __init__(self, profile_id: str):
        if profile_id not in PROMPT_REGISTRY:
            raise ValueError(f"未知的领域配置: {profile_id}")
        self.profile = PROMPT_REGISTRY[profile_id]

    def get_ranker_prompt(self, paper_list_str: str, top_n: int) -> str:
        return f"""
{self.profile['ranker_system']}
请阅读以下论文的标题和摘要。你的任务是从中挑选出最具有{self.profile['ranker_criteria']}的 {top_n} 篇论文。

请直接返回一个 JSON 数组，包含挑选出的论文 ID 和简短的推荐理由。格式如下：
[
    {{"id": 0, "reason": "推荐理由简述"}},
    {{"id": 5, "reason": "推荐理由简述"}}
]

待评价论文列表：
{paper_list_str}
"""

    def get_summary_prompt(self, content: str) -> str:
        return f"""
{self.profile['summary_system']}
你的目标是透过现象看本质，为早报撰写一份极具洞察力的深度解析。
{self.profile['summary_hints']}

{METACOGNITION_JSON_FORMAT}

论文内容：
{content}
"""

    def get_editorial_prompt(self, summaries_str: str) -> str:
        return f"""
{self.profile['editorial_system']}
请根据以下今日精选论文的核心突破，撰写一段 150 字左右的【头版社论】。
要求：
1. 总结今日研究的整体趋势（{self.profile['editorial_hints']}）。
2. 语言风格专业、精炼、具有科技新闻感。
3. 直接输出社论正文，不要包含任何多余的问候语或格式。

今日论文概览：
{summaries_str}
"""
