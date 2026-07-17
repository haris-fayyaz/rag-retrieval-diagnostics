import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Default DB lives at <repo_root>/data/app.db. Override with the
# DATABASE_URL env var (e.g. "sqlite:///:memory:" for tests).
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "app.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"


def get_database_url() -> str:
    """Resolve the database URL, creating the data directory if needed."""
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        db_path = Path(url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return url


def make_engine(database_url: str | None = None):
    """Create a SQLAlchemy engine for the given (or default) database URL."""
    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


# Module-level engine/session factory used by the running application.
engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
