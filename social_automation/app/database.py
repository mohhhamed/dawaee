"""إعداد الاتصال بقاعدة البيانات عبر SQLAlchemy."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# تأكد من وجود مجلد البيانات لملف SQLite
os.makedirs("data", exist_ok=True)

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """مولّد جلسة قاعدة بيانات لاستخدامه في نقاط FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
