"""Vínculo canônico da sessão. O apartamento não é lido do state do modelo.

C08: a API só devolve 201 após persistir vínculo canônico e sessão ADK;
falha parcial não deixa sessão utilizável.
C11: a autorização usa somente SessionIdentity resolvida por
tool_context.session.id; state e argumentos do modelo não mudam apartamento.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

from aurora.config import APP_NAME
from aurora.errors import ApartamentoInexistente

@dataclass(frozen=True)
class SessionIdentity:
    session_id: str
    apartamento: str


def apartamento_existe(engine: Engine, numero: str) -> bool:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT 1 FROM apartamento WHERE numero = :numero"),
            {"numero": numero},
        ).first()
    return row is not None


def obter_identidade(engine: Engine, session_id: str) -> SessionIdentity | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT session_id, apartamento FROM session_identity "
                "WHERE session_id = :session_id"
            ),
            {"session_id": session_id},
        ).mappings().first()
    if row is None:
        return None
    return SessionIdentity(
        session_id=row["session_id"],
        apartamento=row["apartamento"],
    )


def _inserir(engine: Engine, session_id: str, apartamento: str) -> None:
    with engine.begin() as connection:
        existe = connection.execute(
            text("SELECT 1 FROM apartamento WHERE numero = :numero"),
            {"numero": apartamento},
        ).first()
        if existe is None:
            raise ApartamentoInexistente
        connection.execute(
            text(
                "INSERT INTO session_identity (session_id, apartamento, created_at) "
                "VALUES (:session_id, :apartamento, :created_at)"
            ),
            {
                "session_id": session_id,
                "apartamento": apartamento,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )


def _remover(engine: Engine, session_id: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM session_identity WHERE session_id = :session_id"),
            {"session_id": session_id},
        )


async def criar_sessao_coordenada(engine: Engine, session_service, apartamento: str) -> str:
    """Persiste identidade e sessão ADK. Compensa o lado que tiver sido gravado."""
    if not apartamento_existe(engine, apartamento):
        raise ApartamentoInexistente
    session_id = str(uuid4())
    identidade_gravada = False
    adk_gravada = False
    try:
        _inserir(engine, session_id, apartamento)
        identidade_gravada = True
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=session_id,
            session_id=session_id,
        )
        adk_gravada = True
        return session_id
    except Exception:
        if adk_gravada:
            await session_service.delete_session(APP_NAME, session_id, session_id)
        if identidade_gravada:
            _remover(engine, session_id)
        raise
