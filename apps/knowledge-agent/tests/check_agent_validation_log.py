from app.core.database import SessionLocal
from app.services.agent import AgentService


def main() -> None:
    db = SessionLocal()
    try:
        agent = AgentService(db)
        result = agent.run("总结文档")

        print("回答:")
        print(result["answer"])
        print("-" * 40)
        print("工具调用记录:")
        for tool_call in result["tool_calls"]:
            print(tool_call["tool_name"])
            print(tool_call["status"])
            print(tool_call["tool_input"])
    finally:
        db.close()


if __name__ == "__main__":
    main()
