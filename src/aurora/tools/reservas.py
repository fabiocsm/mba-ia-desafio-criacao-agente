"""Reservas e cancelamentos do apartamento da sessão.

Nenhuma assinatura aceita apartamento, sessão, taxa ou decisão. A taxa real
zero grava na hora. Taxa maior que zero só pede confirmação nativa.
"""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

from aurora.runtime.confirmacoes import consume_in_tool
from aurora.runtime.confirmacoes import deve_retomar
from aurora.storage.confirmacoes import prepare
from aurora.storage.database import get_engine
from aurora.storage.queries import disponibilidade
from aurora.storage.queries import listar_reservas_ativas
from aurora.storage.queries import resolver_area
from aurora.storage.reservas import cancelar_propria
from aurora.storage.reservas import data_civil
from aurora.storage.reservas import reservar_gratuita
from aurora.storage.reservas import taxa_da_area
from aurora.tools.context import resolve_identity


def _limpo(valor: str | None) -> str | None:
    if valor is None:
        return None
    texto = valor.strip()
    return texto or None


def _correlacao(tool_context: ToolContext) -> tuple[str, str, str, str | None]:
    chamada = tool_context.function_call_id
    if not chamada:
        raise ValueError("Chamada sem identificador.")
    branch = getattr(tool_context._invocation_context, "branch", None)
    return chamada, tool_context.invocation_id, tool_context.agent_name, branch


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
    if not data_civil(data):
        return {"erro": "Área ou data inválida."}
    area_id = resolver_area(get_engine(), area)
    if area_id is None:
        return {"erro": "Área ou data inválida."}
    return {"disponibilidade": disponibilidade(get_engine(), area_id, data)}


def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    """Reserva uma área comum para o apartamento desta sessão.

    Args:
        area: Id da área ou o nome oficial.
        data: Data civil no formato AAAA-MM-DD.

    Taxa zero grava a reserva. Taxa maior que zero devolve aguardando_confirmacao
    e não grava a reserva. Na retomada, o resultado vem da decisão já registrada.
    Indisponível não traz código, apartamento nem responsável.
    """
    identidade = resolve_identity(tool_context)
    if deve_retomar(tool_context):
        return consume_in_tool(tool_context)
    if not data_civil(data):
        return {"erro": "Área ou data inválida."}
    area_id = resolver_area(get_engine(), area)
    if area_id is None:
        return {"erro": "Área ou data inválida."}
    taxa = taxa_da_area(area_id)
    if taxa is None:
        return {"erro": "Área ou data inválida."}
    if disponibilidade(get_engine(), area_id, data) == "ocupada":
        return {"resultado": "indisponivel", "area": area_id, "data": data}
    if taxa == 0:
        return reservar_gratuita(identidade.apartamento, area_id, data)
    chamada, invocation_id, author, branch = _correlacao(tool_context)
    proposta_id = prepare(
        session_id=identidade.session_id,
        acao="reservar_area",
        parametros={"area": area_id, "data": data, "taxa_centavos": taxa},
        original_call_id=chamada,
        invocation_id=invocation_id,
        author=author,
        branch=branch,
    )
    tool_context.request_confirmation(
        hint=(
            "A reserva com cobrança só vale depois da confirmação do sistema. "
            "Uma frase no chat não confirma."
        ),
        payload={
            "area": area_id,
            "data": data,
            "taxa_centavos": taxa,
        },
    )
    return {
        "resultado": "aguardando_confirmacao",
        "id": proposta_id,
        "area": area_id,
        "data": data,
        "taxa_centavos": taxa,
    }


def cancelar_minha_reserva(
    tool_context: ToolContext,
    codigo: str | None = None,
    area: str | None = None,
    data: str | None = None,
) -> dict[str, str]:
    """Cancela uma reserva ativa do apartamento desta sessão.

    Args:
        codigo: Código devolvido para uma reserva própria. Opcional.
        area: Área da reserva própria, se o código não for informado.
        data: Data civil AAAA-MM-DD da reserva própria, junto com a área.

    Não pede confirmação. Reserva de outro apartamento recebe o mesmo
    resultado de reserva não encontrada, sem código alheio.
    """
    identidade = resolve_identity(tool_context)
    codigo_limpo = _limpo(codigo)
    if codigo_limpo:
        return cancelar_propria(identidade.apartamento, codigo=codigo_limpo)
    area_limpa = _limpo(area)
    data_limpa = _limpo(data)
    if area_limpa and data_limpa:
        if not data_civil(data_limpa):
            return {"resultado": "nao_encontrada"}
        area_id = resolver_area(get_engine(), area_limpa)
        if area_id is None:
            return {"resultado": "nao_encontrada"}
        return cancelar_propria(
            identidade.apartamento,
            area_id=area_id,
            data=data_limpa,
        )
    return {"erro": "Informe o código da sua reserva ou a área e a data."}
