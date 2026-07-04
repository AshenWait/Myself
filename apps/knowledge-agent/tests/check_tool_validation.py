from app.core.database import SessionLocal
from app.services.agent import AgentService


def main() -> None:
    db = SessionLocal()
    try:
        agent = AgentService(db)

        cases = [
            ("summarize_document", {"document_id": None}),
            ("retrieve_documents", {"query": "", "limit": 3}),
            ("retrieve_documents", {"query": "文档", "limit": 999}),
        ]

        for tool_name, tool_input in cases:
            print("=" * 60)
            print("工具:", tool_name)
            print("输入:", tool_input)

            try:
                agent._run_tool(tool_name, tool_input)
            except Exception as exc:
                print("没有执行工具，捕获到错误:")
                print(exc)
    finally:
        db.close()


if __name__ == "__main__":
    main()
