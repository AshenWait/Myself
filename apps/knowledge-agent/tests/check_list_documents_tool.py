from app.core.database import SessionLocal
from app.services.tools import list_documents


def main() -> None:
    db = SessionLocal()
    try:
        documents = list_documents(db)

        print(f"共有 {len(documents)} 个文档")
        for document in documents:
            print("-" * 40)
            print("document_id:", document["document_id"])
            print("filename:", document["filename"])
            print("content_type:", document["content_type"])
            print("page_count:", document["page_count"])
            print("created_at:", document["created_at"])
    finally:
        db.close()


if __name__ == "__main__":
    main()
