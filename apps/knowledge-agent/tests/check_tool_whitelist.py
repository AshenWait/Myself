from app.services.agent import AgentService
from app.services.tool_registry import get_session_tool_whitelist


def main() -> None:
    default_tools = get_session_tool_whitelist("default")
    note_tools = get_session_tool_whitelist("note")

    print("default 会话工具白名单:", default_tools)
    print("note 会话工具白名单:", note_tools)

    # 断言：验证 default_tools 必须包含特定工具
    assert "list_documents" in default_tools
    assert "retrieve_documents" in default_tools
    assert "summarize_document" in default_tools
    assert "create_note" not in default_tools

    assert "create_note" in note_tools
    assert "delete_document" not in note_tools

    limited_agent = AgentService(
        db=None,
        allowed_tools={"list_documents"},
    )

    try:
        limited_agent._run_tool(
            "retrieve_documents",
            {"query": "文档", "limit": 3},
        )
    except PermissionError as exc:
        print("未开放工具被正确拦截:")
        print(exc)
    else:
        raise AssertionError("retrieve_documents 不在白名单中，不应该执行")

    note_agent = AgentService(
        db=None,
        session_type="note",
    )

    try:
        note_agent._run_tool(
            "create_note",
            {
                "title": "测试笔记",
                "content": "note 会话允许看到 create_note，但仍然需要确认。",
                "source_ids": [1],
            },
        )
    except PermissionError as exc:
        print("note 会话中的 create_note 进入权限确认阶段:")
        print(exc)
    else:
        raise AssertionError("create_note 未确认时不应该执行")

    print("Day 45 工具白名单检查通过。")


if __name__ == "__main__":
    main()
