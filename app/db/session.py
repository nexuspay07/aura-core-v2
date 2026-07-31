from app.db.database import SessionLocal

# ==========================================================
# DATABASE DEPENDENCY
# ==========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ==========================================================
# BACKWARD COMPATIBILITY
# ==========================================================

db_session = SessionLocal()