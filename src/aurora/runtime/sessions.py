"""Sessão ADK em disco, com timestamp estritamente crescente por sessão.

C09: eventos persistidos são integrais, imutáveis e retornados na ordem de
gravação; ler não altera nem cria eventos.
C10: timestamp de novo evento é estritamente maior que o anterior da sessão,
com passo mínimo de 1 ms, inclusive após reinício.

O lock desta classe só cobre a atribuição do timestamp. A persistência nativa
corre depois, com o lock do SDK, para não haver espera cruzada.
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime
from pathlib import Path

from google.adk.events.event import Event
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.session import Session
from sqlalchemy import event as sa_event
from sqlalchemy import func
from sqlalchemy import select
from typing_extensions import override

_MIN_STEP_SECONDS = 0.001


def adk_database_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def tune_sqlite(service: DatabaseSessionService) -> None:
    def _pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    sa_event.listen(service.db_engine.sync_engine, "connect", _pragmas)


def _to_seconds(value: object) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.strip().replace(" ", "T"))
        return parsed.timestamp()
    raise TypeError(f"Timestamp persistido ilegível ({type(value).__name__}).")


def _millis(seconds: float) -> int:
    return int(math.floor(seconds * 1000 + 1e-6))


class OrderedDatabaseSessionService(DatabaseSessionService):
    """DatabaseSessionService com ordem temporal estável após reinício."""

    def __init__(self, db_url: str):
        super().__init__(db_url)
        self._ts_guard = asyncio.Lock()
        self._last_ms: dict[str, int] = {}
        self._floors_loaded = False

    async def prime_timestamps(self) -> None:
        async with self._ts_guard:
            await self._load_floors()

    async def _load_floors(self) -> None:
        if self._floors_loaded:
            return
        await self._prepare_tables()
        schema = self._get_schema_classes()
        async with self.database_session_factory() as sql_session:
            statement = select(
                schema.StorageEvent.session_id,
                func.max(schema.StorageEvent.timestamp),
            ).group_by(schema.StorageEvent.session_id)
            result = await sql_session.execute(statement)
            rows = result.all()
        for session_id, max_timestamp in rows:
            if max_timestamp is None:
                continue
            seconds = _to_seconds(max_timestamp)
            minimum_next = _millis(seconds) + 1
            if minimum_next / 1000 < seconds + _MIN_STEP_SECONDS:
                minimum_next = _millis(seconds + _MIN_STEP_SECONDS) + 1
            self._last_ms[session_id] = max(
                self._last_ms.get(session_id, 0),
                minimum_next - 1,
            )
        self._floors_loaded = True

    def _allocate(self, session_id: str, proposed: float) -> float:
        floor_ms = self._last_ms.get(session_id, 0)
        proposed_ms = _millis(proposed)
        chosen = proposed_ms if proposed_ms > floor_ms else floor_ms + 1
        if chosen / 1000 < (floor_ms / 1000) + _MIN_STEP_SECONDS:
            chosen = floor_ms + 1
        self._last_ms[session_id] = chosen
        return chosen / 1000

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        if not event.partial:
            async with self._ts_guard:
                await self._load_floors()
                event.timestamp = self._allocate(session.id, float(event.timestamp))
        return await super().append_event(session=session, event=event)
