from app.core.database import SessionLocal
from app.models import ChatMessage, ChatSession, Document


def main() -> None:
    db = SessionLocal()

    try:
        document = Document(
            filename="demo.txt",
            file_path="storage/uploads/demo.txt",
            content_type="text/plain",
            page_count=1,
        )

        chat_session = ChatSession(title="First Chat")

        db.add(document)
        db.add(chat_session)
        db.commit()

        db.refresh(document)
        db.refresh(chat_session)

        message = ChatMessage(
            session_id=chat_session.id,
            role="user",
            content="你好，这是第一条测试消息",
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        print(f"created document id: {document.id}")
        print(f"created chat session id: {chat_session.id}")
        print(f"created chat message id: {message.id}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
