"""Consulta de visitantes do apartamento da sessão. Sem parâmetro de apartamento."""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

from aurora.storage.database import get_engine
from aurora.storage.queries import listar_visitantes
from aurora.tools.context import resolve_identity


def listar_meus_visitantes(tool_context: ToolContext) -> list[dict[str, str]]:
    """Lista os visitantes do apartamento desta sessão.

    Não recebe apartamento nem sessão. Cada item traz somente nome e data.
    """
    identidade = resolve_identity(tool_context)
    return listar_visitantes(get_engine(), identidade.apartamento)
