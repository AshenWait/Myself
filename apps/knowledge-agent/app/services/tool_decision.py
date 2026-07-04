from app.services.llm import LLMService


def decide_tool(user_message: str) -> str:
    """让模型判断用户问题是否需要调用文档检索工具。"""
    llm = LLMService()

    prompt = f"""
你是 Knowledge Agent 的工具选择器。

你只能输出下面两个结果之一：
- retrieve_documents
- none

判断规则：
如果用户问题需要查询已上传文档、资料、知识库，就输出 retrieve_documents。
如果只是寒暄、闲聊、感谢、打招呼，就输出 none。

用户问题：
{user_message}

请只输出工具名，不要解释。
"""

    answer, _ = llm.chat(prompt)
    tool_name = answer.strip()

    if tool_name == "retrieve_documents":
        return "retrieve_documents"

    return "none"
