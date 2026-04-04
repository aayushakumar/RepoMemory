"""Database engine, session factory, and base model."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from repomemory.config import settings


class Base(DeclarativeBase):
    pass


def _get_engine(db_path=None):
    path = db_path or settings.get_db_path()
    engine = create_engine(f"sqlite:///{path}", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings.ensure_dirs()
        _engine = _get_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_session() -> Session:
    factory = get_session_factory()
    return factory()


def init_db():
    """Create all tables."""
    from repomemory.models.tables import _register_all  # noqa: F401

    _register_all()
    Base.metadata.create_all(get_engine())


def reset_engine():
    """Reset cached engine/session (for testing)."""
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
