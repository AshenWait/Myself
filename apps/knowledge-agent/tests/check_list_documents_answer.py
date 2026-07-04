from app.core.database import SessionLocal
from app.services.tools import list_documents


def build_documents_answer(documents: list[dict]) -> str:
    if not documents:
        return "你还没有上传任何文档。"

    lines = ["你已经上传了这些文档："]

    for document in documents:
        lines.append(
            f'- #{document["document_id"]} {document["filename"]}，'
            f'{document["page_count"]} 页'
        )

    return "\n".join(lines)


def main() -> None:
    db = SessionLocal()
    try:
        documents = list_documents(db)
        answer = build_documents_answer(documents)
        print(answer)
    finally:
        db.close()


if __name__ == "__main__":
    main()
