from app.services.agent import AgentService
from app.services.tool_registry import ensure_tool_can_execute


def main() -> None:
    agent = AgentService(db=None, session_type="note")


    try:
        agent._run_tool(
            "create_note",
            {
                "title": "测试笔记",
                "content": "这条笔记没有确认，所以不能写入。",
                "source_ids": [1],
            },
        )
    except PermissionError as exc:
        print("未确认时，create_note 被正确拦截：")
        print(exc)
    else:
        raise AssertionError("create_note 未确认时不应该执行")

    ensure_tool_can_execute("create_note", confirmed=True)
    print("确认后，create_note 通过权限检查。")

    try:
        ensure_tool_can_execute("delete_document", confirmed=True)
    except PermissionError as exc:
        print("即使确认，危险工具也被正确拦截：")
        print(exc)
    else:
        raise AssertionError("delete_document 不应该允许执行")

    print("Day 44 工具确认检查通过。")


if __name__ == "__main__":
    main()
