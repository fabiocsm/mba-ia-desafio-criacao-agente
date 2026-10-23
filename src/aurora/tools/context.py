"""Resolve a identidade canônica antes de qualquer SQL de morador.

A sessão vem de tool_context.session.id. State e argumentos do modelo
não escolhem o apartamento.
"""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

from aurora.storage.database import get_engine
from aurora.storage.identity import SessionIdentity, obter_identidade


class IdentidadeIndisponivel(Exception):
    """A ferramenta não tem sessão correlacionada ao vínculo canônico."""


def resolve_identity(tool_context: ToolContext) -> SessionIdentity:
    session = getattr(tool_context, "session", None)
    session_id = getattr(session, "id", None)
    if not isinstance(session_id, str) or not session_id:
        raise IdentidadeIndisponivel("Sessão sem autorização.")
    identidade = obter_identidade(get_engine(), session_id)
    if identidade is None:
        raise IdentidadeIndisponivel("Sessão sem autorização.")
    return identidade
