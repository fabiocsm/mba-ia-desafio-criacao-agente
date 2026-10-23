"""Retomada nativa da confirmação no agente que pediu a tool.

A rota não executa reserva nem autorização. Ela grava a decisão e devolve ao
Runner a resposta da função adk_request_confirmation. O ContextVar só existe
durante essa retomada e é desfeito no finally. O executor corre dentro do
consumo, na conexão dessa transação, com a proposta e a sessão canônicas.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from contextvars import ContextVar
from dataclasses import dataclass

from google.adk.events.event import Event
from google.adk.runners import Runner
from google.genai import types

from aurora.storage.confirmacoes import DecisaoRegistrada
from aurora.storage.confirmacoes import consumir
from aurora.tools.context import resolve_identity

logger = logging.getLogger(__name__)

NOME_FUNCAO = "adk_request_confirmation"


@dataclass(frozen=True)
class RetomadaAutorizada:
    session_id: str
    invocation_id: str
    author: str
    proposta_id: str
    original_function_call_id: str


_retomada: ContextVar[RetomadaAutorizada | None] = ContextVar(
    "aurora_retomada",
    default=None,
)


def retomada_atual() -> RetomadaAutorizada | None:
    return _retomada.get()


def deve_retomar(tool_context) -> bool:
    """O fallback identifica só a chamada original, não novas tools do Runner."""
    if getattr(tool_context, "tool_confirmation", None) is not None:
        return True
    atual = _retomada.get()
    if atual is None:
        return False
    sessao = getattr(getattr(tool_context, "session", None), "id", None)
    return (
        sessao == atual.session_id
        and getattr(tool_context, "function_call_id", None)
        == atual.original_function_call_id
        and tool_context.invocation_id == atual.invocation_id
        and tool_context.agent_name == atual.author
    )


def consume_in_tool(tool_context) -> dict:
    """Efeito somente com decisão persistida e correlação desta retomada."""
    identidade = resolve_identity(tool_context)
    autorizada = _retomada.get()
    chamada = getattr(tool_context, "function_call_id", None)
    if (
        autorizada is None
        or not chamada
        or chamada != autorizada.original_function_call_id
        or autorizada.session_id != identidade.session_id
        or autorizada.invocation_id != tool_context.invocation_id
        or autorizada.author != tool_context.agent_name
    ):
        return {"resultado": "nao_autorizada"}
    return consumir(
        proposta_id=autorizada.proposta_id,
        session_id=identidade.session_id,
        apartamento=identidade.apartamento,
        original_call_id=chamada,
    )


def retomada_persistida(eventos, decisao: DecisaoRegistrada) -> bool:
    """Há resposta nativa e, depois dela, o retorno da tool original."""
    viu_confirmacao = False
    for evento in eventos:
        obter = getattr(evento, "get_function_responses", None)
        if obter is None:
            continue
        for resposta in obter() or []:
            if (
                resposta.id == decisao.native_confirmation_id
                and resposta.name == NOME_FUNCAO
            ):
                viu_confirmacao = True
            if viu_confirmacao and resposta.id == decisao.original_function_call_id:
                return True
    return False


def conteudo_da_decisao(decisao: DecisaoRegistrada) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name=NOME_FUNCAO,
                    id=decisao.native_confirmation_id,
                    response={"confirmed": decisao.confirmado},
                )
            )
        ],
    )


class ConfirmationCoordinator:
    """Monta a resposta nativa e retoma o Runner. Não chama o executor."""

    def __init__(self, runner: Runner):
        self.runner = runner

    def instalar(self, decisao: DecisaoRegistrada):
        return _retomada.set(
            RetomadaAutorizada(
                session_id=decisao.session_id,
                invocation_id=decisao.invocation_id,
                author=decisao.author,
                proposta_id=decisao.proposta_id,
                original_function_call_id=decisao.original_function_call_id,
            )
        )

    def encerrar(self, token) -> None:
        _retomada.reset(token)

    async def resume(self, decisao: DecisaoRegistrada, run_config) -> AsyncIterator[Event]:
        """Retoma a invocação original. Não executa a reserva aqui."""
        token = self.instalar(decisao)
        try:
            async with aclosing(
                self.runner.run_async(
                    user_id=decisao.session_id,
                    session_id=decisao.session_id,
                    invocation_id=decisao.invocation_id,
                    new_message=conteudo_da_decisao(decisao),
                    run_config=run_config,
                )
            ) as eventos:
                async for evento in eventos:
                    yield evento
        finally:
            self.encerrar(token)

    def autores_divergentes(self, eventos, author: str) -> bool:
        """Verdadeiro se alguma resposta da tool original saiu de outro agente."""
        for evento in eventos:
            obter = getattr(evento, "get_function_responses", None)
            if obter is None:
                continue
            for resposta in obter() or []:
                if resposta.name == NOME_FUNCAO:
                    continue
                if evento.author and evento.author != author and evento.author != "user":
                    logger.warning(
                        "Retomada produzida por %s; solicitante canonico %s",
                        evento.author,
                        author,
                    )
                    return True
        return False


def registrar_executor_visitante() -> None:
    """Registra autorizar_visitante no mapa herdado. Não cria outro coordenador."""
    from aurora.storage.confirmacoes import registrar_executor
    from aurora.storage.visitantes import executar_autorizacao
    from aurora.storage.visitantes import validar_parametros_visitante

    registrar_executor(
        "autorizar_visitante",
        validar=validar_parametros_visitante,
        executar=executar_autorizacao,
    )
