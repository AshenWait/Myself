from app.core.database import SessionLocal
from app.services.tools import retrieve_documents


def main() -> None:
    db = SessionLocal()
    try:
        results = retrieve_documents(db, query="这个文档主要讲了什么？", limit=3)

        print(f"检索到 {len(results)} 个片段")
        for item in results:
            print("-" * 40)
            print("chunk_id:", item["chunk_id"])
            print("document_id:", item["document_id"])
            print("page_number:", item["page_number"])
            print("distance:", item["distance"])
            print("content:", item["content"][:120])
    finally:
        db.close()


if __name__ == "__main__":
    main()
