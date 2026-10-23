"""Conexões SQLite do banco de negócio.

O banco do ADK fica em outro arquivo. Nenhuma transação daqui permanece
aberta durante chamada ao Gemini: cada operação abre e fecha a sua.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from aurora.config import get_settings

_engine: Engine | None = None


def _tune_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        path = settings.business_db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            f"sqlite:///{path.as_posix()}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        event.listen(engine, "connect", _tune_sqlite)
        _engine = engine
    return _engine


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
