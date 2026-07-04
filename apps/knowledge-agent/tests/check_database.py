from app.core.database import check_database_connection

if __name__ == "__main__":
    ok = check_database_connection()
    print(f"database connection ok: {ok}")
