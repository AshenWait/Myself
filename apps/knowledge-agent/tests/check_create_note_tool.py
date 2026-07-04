from app.core.database import SessionLocal
from app.services.tools import create_note


def main() -> None:
    db = SessionLocal()
    try:
        result = create_note(
            db=db,
            title="Day 39 测试笔记",
            content="这是一条由 create_note 工具保存的测试笔记。",
            source_ids=[1],
        )

        print("note_id:", result["note_id"])
        print("title:", result["title"])
        print("content:", result["content"])
        print("source_chunk_ids:", result["source_chunk_ids"])
        print("created_at:", result["created_at"])
    finally:
        db.close()


if __name__ == "__main__":
    main()
