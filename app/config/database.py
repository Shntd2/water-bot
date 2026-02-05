from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import settings


def get_database_url() -> str:
    url = settings.POSTGRES_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(
    get_database_url(),
    echo=settings.POSTGRES_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "sslmode": "require",
        "channel_binding": "require"
    } if "sslmode" not in settings.POSTGRES_URL else {}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    from app.models.user_model import User

    Base.metadata.create_all(bind=engine)
