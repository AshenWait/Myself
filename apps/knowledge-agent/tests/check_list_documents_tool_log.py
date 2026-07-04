from app.core.database import SessionLocal
from app.services.tools import list_documents


def main() -> None:
    db = SessionLocal()
    try:
        tool_name = "list_documents"
        tool_input = {}

        documents = list_documents(db)

        tool_log = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "result_count": len(documents),
            "status": "success",
        }

        print(tool_log)
    finally:
        db.close()


if __name__ == "__main__":
    main()
