from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///chat.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_column(conn, table: str, column: str, ddl: str):
    """SQLite 轻量迁移：表已存在时补充新增列（无迁移工具，只能手工加列）"""
    cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]
    if column not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def init_db():
    from backend.models import Base as _  # noqa: F401 确保模型被导入
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _ensure_column(conn, "conversations", "conv_type",
                       "conv_type VARCHAR(20) DEFAULT 'chat'")
        _ensure_column(conn, "conversations", "last_frame_path",
                       "last_frame_path VARCHAR(500)")
        _ensure_column(conn, "conversations", "merged_video_path",
                       "merged_video_path VARCHAR(500)")
        _ensure_column(conn, "conversations", "megapixels",
                       "megapixels FLOAT DEFAULT 0.8")
        _ensure_column(conn, "conversations", "steps",
                       "steps INTEGER DEFAULT 8")
        _ensure_column(conn, "conversations", "duration",
                       "duration INTEGER DEFAULT 5")
        _ensure_column(conn, "conversations", "keep_audio",
                       "keep_audio INTEGER DEFAULT 0")
        _ensure_column(conn, "conversations", "parent_conversation_id",
                       "parent_conversation_id INTEGER")
        _ensure_column(conn, "conversations", "fork_from_message_id",
                       "fork_from_message_id INTEGER")
        _ensure_column(conn, "conversations", "model",
                       "model VARCHAR(40) DEFAULT 'deepseek'")
        conn.commit()
