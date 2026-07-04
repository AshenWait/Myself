from app.core.database import SessionLocal
from app.services.agent import AgentService


def main() -> None:
    db = SessionLocal()
    try:
        agent = AgentService(db)

        questions = [
            "我上传了哪些文档？",
            "总结文档 1",
            "这个文档主要讲了什么？",
            "总结文档 999999",
            "你好",
        ]

        for question in questions:
            print("=" * 60)
            print("用户问题:", question)

            result = agent.run(question)

            print("回答:")
            print(result["answer"])
            print("工具调用次数:", len(result["tool_calls"]))

            for tool_call in result["tool_calls"]:
                print("工具名:", tool_call["tool_name"])
                print("工具输入:", tool_call["tool_input"])
                print("状态:", tool_call["status"])
    finally:
        db.close()


if __name__ == "__main__":
    main()
