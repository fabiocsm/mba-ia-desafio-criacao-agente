"""Consultas de reservas e disponibilidade. Sem parâmetro de apartamento."""

from __future__ import annotations

from datetime import datetime

from google.adk.tools.tool_context import ToolContext

from aurora.storage.database import get_engine
from aurora.storage.queries import disponibilidade, listar_reservas_ativas, resolver_area
from aurora.tools.context import resolve_identity


def _data_civil(valor: str) -> bool:
    if len(valor) != 10 or valor[4] != "-" or valor[7] != "-":
        return False
    try:
        datetime.strptime(valor, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def listar_minhas_reservas(tool_context: ToolContext) -> list[dict[str, str]]:
    """Lista as reservas ativas do apartamento desta sessão.

    Não recebe apartamento nem sessão. Cada item traz somente codigo, area e data.
    """
    identidade = resolve_identity(tool_context)
    return listar_reservas_ativas(get_engine(), identidade.apartamento)


def consultar_disponibilidade(
    area: str,
    data: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Informa se uma área comum está livre ou ocupada numa data.

    Args:
        area: Id da área (salao-de-festas, churrasqueira ou quadra) ou o nome oficial.
        data: Data civil no formato AAAA-MM-DD.

    O retorno traz disponibilidade, livre ou ocupada, ou o campo erro.
    Não inclui código, apartamento nem responsável.
    """
    resolve_identity(tool_context)
    if not _data_civil(data):
        return {"erro": "Área ou data inválida."}
    area_id = resolver_area(get_engine(), area)
    if area_id is None:
        return {"erro": "Área ou data inválida."}
    return {"disponibilidade": disponibilidade(get_engine(), area_id, data)}
