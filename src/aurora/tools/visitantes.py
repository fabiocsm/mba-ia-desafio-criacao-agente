"""Visitantes do apartamento da sessão.

Nenhuma assinatura aceita apartamento, sessão ou decisão. A autorização só
pede confirmação nativa. A gravação ocorre na reentrada, com o snapshot do banco.
"""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

from aurora.runtime.confirmacoes import consume_in_tool
from aurora.runtime.confirmacoes import deve_retomar
from aurora.storage.confirmacoes import prepare
from aurora.storage.database import get_engine
from aurora.storage.queries import listar_visitantes
from aurora.storage.reservas import data_civil
from aurora.tools.context import resolve_identity


def _correlacao(tool_context: ToolContext) -> tuple[str, str, str, str | None]:
    chamada = tool_context.function_call_id
    if not chamada:
        raise ValueError("Chamada sem identificador.")
    branch = getattr(tool_context._invocation_context, "branch", None)
    return chamada, tool_context.invocation_id, tool_context.agent_name, branch


def listar_meus_visitantes(tool_context: ToolContext) -> list[dict[str, str]]:
    """Lista os visitantes do apartamento desta sessão.

    Não recebe apartamento nem sessão. Cada item traz somente nome e data.
    Lista vazia é uma lista vazia, sem consulta a outro apartamento.
    """
    identidade = resolve_identity(tool_context)
    return listar_visitantes(get_engine(), identidade.apartamento)


def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
    """Prepara a autorização de entrada de um visitante.

    Args:
        nome: Nome do visitante.
        data: Data civil no formato AAAA-MM-DD.

    Sem nome ou sem data, pede esclarecimento e não cria pendência. Data
    inválida também não cria pendência. O texto do morador não autoriza.
    Na retomada, o resultado vem da decisão já registrada, com o nome e a
    data congelados na proposta. Não grava o visitante nesta chamada inicial.
    """
    identidade = resolve_identity(tool_context)
    if deve_retomar(tool_context):
        return consume_in_tool(tool_context)
    nome_limpo = nome.strip() if isinstance(nome, str) else ""
    data_limpa = data.strip() if isinstance(data, str) else ""
    if not nome_limpo or not data_limpa:
        return {"erro": "Informe o nome do visitante e a data AAAA-MM-DD."}
    if not data_civil(data_limpa):
        return {"erro": "Data inválida. Use AAAA-MM-DD."}
    chamada, invocation_id, author, branch = _correlacao(tool_context)
    proposta_id = prepare(
        session_id=identidade.session_id,
        acao="autorizar_visitante",
        parametros={"nome": nome_limpo, "data": data_limpa},
        original_call_id=chamada,
        invocation_id=invocation_id,
        author=author,
        branch=branch,
    )
    tool_context.request_confirmation(
        hint=(
            "A entrada só vale depois da confirmação do sistema. "
            "Uma frase no chat não autoriza."
        ),
        payload={"nome": nome_limpo, "data": data_limpa},
    )
    return {
        "resultado": "aguardando_confirmacao",
        "id": proposta_id,
        "nome": nome_limpo,
        "data": data_limpa,
    }
