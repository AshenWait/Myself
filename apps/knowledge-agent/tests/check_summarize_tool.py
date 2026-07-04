from app.core.database import SessionLocal
from app.services.tools import summarize_document


def main() -> None:
    db = SessionLocal()
    try:
        result = summarize_document(db, document_id=1)

        print("文档 ID:", result["document_id"])
        print("文档名:", result["document_filename"])
        print("耗时:", result["latency_ms"], "ms")
        print("-" * 40)
        print(result["summary"])
        print("-" * 40)
        print("引用来源数量:", len(result["sources"]))

        for source in result["sources"]:
            print(
                f'chunk_id={source["chunk_id"]}, '
                f'page={source["page_number"]}, '
                f'chunk_index={source["chunk_index"]}'
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
