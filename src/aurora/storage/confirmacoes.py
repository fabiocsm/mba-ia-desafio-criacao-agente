"""Proposta imutável, decisão sistêmica e consumo do efeito.

Somente a rota grava a decisão. A tool consome essa decisão na mesma
transação do efeito. Texto, state e ToolConfirmation não autorizam.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from aurora.errors import ConfirmacaoConflito
from aurora.storage.database import get_engine
from aurora.storage.database import transacao_escrita

Executor = Callable[[Connection, str, dict], dict]
Validador = Callable[[dict], dict]


@dataclass(frozen=True)
class AcaoRegistrada:
    validar: Validador
    executar: Executor


@dataclass(frozen=True)
class DecisaoRegistrada:
    proposta_id: str
    session_id: str
    invocation_id: str
    author: str
    branch: str | None
    native_confirmation_id: str
    original_function_call_id: str
    confirmado: bool
    acao: str


_ACOES: dict[str, AcaoRegistrada] = {}


def registrar_executor(acao: str, *, validar: Validador, executar: Executor) -> None:
    """Registra uma ação que pode congelar parâmetros e consumir decisão.

    O executor recebe a conexão já aberta e não pode fazer commit próprio.
    A spec 003 registra autorizar_visitante neste mesmo mapa.
    """
    _ACOES[acao] = AcaoRegistrada(validar=validar, executar=executar)


def acao_registrada(acao: str) -> AcaoRegistrada | None:
    return _ACOES.get(acao)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(parametros: dict) -> str:
    return json.dumps(parametros, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def prepare(
    *,
    session_id: str,
    acao: str,
    parametros: dict,
    original_call_id: str,
    invocation_id: str,
    author: str,
    branch: str | None,
) -> str:
    """Insere proposta preparando, ou devolve a já gravada para a mesma chamada."""
    registrada = _ACOES.get(acao)
    if registrada is None:
        raise ValueError("Ação de confirmação não registrada.")
    if not original_call_id or not invocation_id or not author:
        raise ValueError("Correlação da chamada incompleta.")
    congelados = registrada.validar(parametros)
    payload = _json(congelados)
    with transacao_escrita() as connection:
        existente = connection.execute(
            text(
                """
                SELECT id FROM proposta_confirmacao
                WHERE session_id = :session_id
                  AND invocation_id = :invocation_id
                  AND original_function_call_id = :original_call_id
                """
            ),
            {
                "session_id": session_id,
                "invocation_id": invocation_id,
                "original_call_id": original_call_id,
            },
        ).scalar()
        if existente is not None:
            return str(existente)
        proposta_id = str(uuid4())
        connection.execute(
            text(
                """
                INSERT INTO proposta_confirmacao (
                    id, session_id, acao, parametros_json,
                    original_function_call_id, native_confirmation_id,
                    invocation_id, author, branch, fase, created_at
                ) VALUES (
                    :id, :session_id, :acao, :parametros_json,
                    :original_call_id, NULL,
                    :invocation_id, :author, :branch, 'preparando', :created_at
                )
                """
            ),
            {
                "id": proposta_id,
                "session_id": session_id,
                "acao": acao,
                "parametros_json": payload,
                "original_call_id": original_call_id,
                "invocation_id": invocation_id,
                "author": author,
                "branch": branch,
                "created_at": _agora(),
            },
        )
    return proposta_id


def _como_dict(valor: Any) -> dict:
    if valor is None:
        return {}
    if isinstance(valor, dict):
        return valor
    dump = getattr(valor, "model_dump", None)
    if dump is not None:
        return dump()
    return dict(valor)


def publish_from_event(event: Any, session_id: str) -> None:
    """Publica pendência depois que o evento ADK já foi persistido.

    Não cria nem regrava eventos. Proposta sem o evento correspondente
    permanece em preparando e não entra na lista pública.
    """
    obter = getattr(event, "get_function_calls", None)
    if obter is None:
        return
    chamadas = obter() or []
    invocation_id = getattr(event, "invocation_id", None)
    author = getattr(event, "author", None)
    branch = getattr(event, "branch", None)
    if not invocation_id or not author:
        return
    for chamada in chamadas:
        if getattr(chamada, "name", None) != "adk_request_confirmation":
            continue
        native_id = getattr(chamada, "id", None)
        args = _como_dict(getattr(chamada, "args", None))
        original = _como_dict(args.get("originalFunctionCall"))
        original_id = original.get("id")
        if not native_id or not original_id:
            continue
        with transacao_escrita() as connection:
            linha = connection.execute(
                text(
                    """
                    SELECT id, branch
                    FROM proposta_confirmacao
                    WHERE session_id = :session_id
                      AND invocation_id = :invocation_id
                      AND original_function_call_id = :original_id
                      AND author = :author
                      AND fase = 'preparando'
                      AND native_confirmation_id IS NULL
                    """
                ),
                {
                    "session_id": session_id,
                    "invocation_id": invocation_id,
                    "original_id": original_id,
                    "author": author,
                },
            ).mappings().first()
            if linha is None:
                continue
            gravado = linha["branch"]
            if gravado and branch and gravado != branch:
                continue
            connection.execute(
                text(
                    """
                    UPDATE proposta_confirmacao
                    SET native_confirmation_id = :native_id, fase = 'pendente'
                    WHERE id = :id
                      AND fase = 'preparando'
                      AND native_confirmation_id IS NULL
                    """
                ),
                {"native_id": native_id, "id": linha["id"]},
            )


def sessoes_preparando() -> list[str]:
    with get_engine().connect() as connection:
        linhas = connection.execute(
            text(
                """
                SELECT DISTINCT session_id
                FROM proposta_confirmacao
                WHERE fase = 'preparando' AND native_confirmation_id IS NULL
                ORDER BY session_id
                """
            )
        ).all()
    return [linha[0] for linha in linhas]


def decide(session_id: str, proposta_id: str, confirmado: bool) -> DecisaoRegistrada:
    """CAS de pendência da própria sessão para decisão e despacho recuperar.

    ID ausente, de outra sessão ou já respondido levanta ConfirmacaoConflito
    sem alterar linhas.
    """
    if not isinstance(confirmado, bool):
        raise ConfirmacaoConflito
    marca = _agora()
    with transacao_escrita() as connection:
        connection.execute(
            text(
                """
                INSERT INTO decisao_confirmacao (
                    proposta_id, confirmado, decidida_em, consumida_em, resultado_json
                )
                SELECT proposta.id, :confirmado, :decidida_em, NULL, NULL
                FROM proposta_confirmacao AS proposta
                WHERE proposta.id = :proposta_id
                  AND proposta.session_id = :session_id
                  AND proposta.fase = 'pendente'
                  AND proposta.native_confirmation_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM decisao_confirmacao
                    WHERE proposta_id = proposta.id
                  )
                """
            ),
            {
                "confirmado": 1 if confirmado else 0,
                "decidida_em": marca,
                "proposta_id": proposta_id,
                "session_id": session_id,
            },
        )
        gravada = connection.execute(
            text(
                """
                SELECT 1 FROM decisao_confirmacao
                WHERE proposta_id = :proposta_id AND decidida_em = :decidida_em
                """
            ),
            {"proposta_id": proposta_id, "decidida_em": marca},
        ).first()
        if gravada is None:
            raise ConfirmacaoConflito
        connection.execute(
            text(
                """
                INSERT INTO despacho_retomada (proposta_id, estado, ultima_falha)
                VALUES (:proposta_id, 'recuperar', NULL)
                """
            ),
            {"proposta_id": proposta_id},
        )
        linha = connection.execute(
            text(
                """
                SELECT invocation_id, author, branch, native_confirmation_id,
                       original_function_call_id, acao
                FROM proposta_confirmacao
                WHERE id = :proposta_id AND session_id = :session_id
                """
            ),
            {"proposta_id": proposta_id, "session_id": session_id},
        ).mappings().one()
    return DecisaoRegistrada(
        proposta_id=proposta_id,
        session_id=session_id,
        invocation_id=linha["invocation_id"],
        author=linha["author"],
        branch=linha["branch"],
        native_confirmation_id=linha["native_confirmation_id"],
        original_function_call_id=linha["original_function_call_id"],
        confirmado=confirmado,
        acao=linha["acao"],
    )


def detalhes_publicos(acao: str, parametros: dict) -> dict[str, Any]:
    if acao == "reservar_area":
        return {
            "area": parametros["area"],
            "data": parametros["data"],
            "taxa_centavos": parametros["taxa_centavos"],
        }
    if acao == "autorizar_visitante":
        return {"nome": parametros["nome"], "data": parametros["data"]}
    return {}


def list_pending(session_id: str) -> list[dict[str, Any]]:
    """Pendências publicadas desta sessão que ainda não têm decisão."""
    with get_engine().connect() as connection:
        linhas = connection.execute(
            text(
                """
                SELECT proposta.id, proposta.acao, proposta.parametros_json
                FROM proposta_confirmacao AS proposta
                LEFT JOIN decisao_confirmacao AS decisao
                  ON decisao.proposta_id = proposta.id
                WHERE proposta.session_id = :session_id
                  AND proposta.fase = 'pendente'
                  AND decisao.proposta_id IS NULL
                ORDER BY proposta.created_at, proposta.id
                """
            ),
            {"session_id": session_id},
        ).mappings()
        pendencias = []
        for linha in linhas:
            parametros = json.loads(linha["parametros_json"])
            pendencias.append(
                {
                    "id": linha["id"],
                    "acao": linha["acao"],
                    "detalhes": detalhes_publicos(linha["acao"], parametros),
                }
            )
    return pendencias


def registrar_falha(proposta_id: str, falha: str) -> None:
    limpa = "".join(
        caractere
        for caractere in falha
        if caractere.isascii() and (caractere.isalnum() or caractere in "._-")
    )[:80]
    if not limpa:
        limpa = "falha_tecnica"
    with transacao_escrita() as connection:
        connection.execute(
            text(
                """
                UPDATE despacho_retomada
                SET ultima_falha = :falha
                WHERE proposta_id = :proposta_id AND estado = 'recuperar'
                """
            ),
            {"falha": limpa, "proposta_id": proposta_id},
        )


def despachos_recuperar(session_id: str) -> list[DecisaoRegistrada]:
    with get_engine().connect() as connection:
        linhas = connection.execute(
            text(
                """
                SELECT proposta.id, proposta.invocation_id, proposta.author,
                       proposta.branch, proposta.native_confirmation_id,
                       proposta.original_function_call_id, proposta.acao,
                       decisao.confirmado
                FROM despacho_retomada AS despacho
                JOIN decisao_confirmacao AS decisao
                  ON decisao.proposta_id = despacho.proposta_id
                JOIN proposta_confirmacao AS proposta
                  ON proposta.id = despacho.proposta_id
                WHERE proposta.session_id = :session_id
                  AND despacho.estado = 'recuperar'
                ORDER BY decisao.decidida_em, proposta.id
                """
            ),
            {"session_id": session_id},
        ).mappings()
        return [
            DecisaoRegistrada(
                proposta_id=linha["id"],
                session_id=session_id,
                invocation_id=linha["invocation_id"],
                author=linha["author"],
                branch=linha["branch"],
                native_confirmation_id=linha["native_confirmation_id"],
                original_function_call_id=linha["original_function_call_id"],
                confirmado=bool(linha["confirmado"]),
                acao=linha["acao"],
            )
            for linha in linhas
        ]


def consumida(proposta_id: str) -> bool:
    with get_engine().connect() as connection:
        marca = connection.execute(
            text(
                """
                SELECT consumida_em FROM decisao_confirmacao
                WHERE proposta_id = :proposta_id
                """
            ),
            {"proposta_id": proposta_id},
        ).scalar()
    return marca is not None


def marcar_concluido(proposta_id: str) -> None:
    with transacao_escrita() as connection:
        connection.execute(
            text(
                """
                UPDATE despacho_retomada
                SET estado = 'concluido'
                WHERE proposta_id = :proposta_id AND estado = 'recuperar'
                """
            ),
            {"proposta_id": proposta_id},
        )


def consumir(
    *,
    proposta_id: str,
    session_id: str,
    apartamento: str,
    original_call_id: str,
) -> dict[str, Any]:
    """Consome a decisão e grava o efeito, ou devolve o resultado já gravado.

    Sem decisão persistida não há efeito. Parâmetros executados são os do
    banco. Reentrada devolve o JSON próprio sem emitir outro código.
    """
    with transacao_escrita() as connection:
        linha = connection.execute(
            text(
                """
                SELECT decisao.confirmado, decisao.consumida_em, decisao.resultado_json,
                       proposta.acao, proposta.parametros_json,
                       proposta.original_function_call_id, proposta.session_id
                FROM decisao_confirmacao AS decisao
                JOIN proposta_confirmacao AS proposta
                  ON proposta.id = decisao.proposta_id
                WHERE decisao.proposta_id = :proposta_id
                """
            ),
            {"proposta_id": proposta_id},
        ).mappings().first()
        if linha is None:
            return {"resultado": "nao_autorizada"}
        if (
            linha["session_id"] != session_id
            or linha["original_function_call_id"] != original_call_id
        ):
            return {"resultado": "nao_autorizada"}
        if linha["consumida_em"] is not None:
            return json.loads(linha["resultado_json"])
        if not linha["confirmado"]:
            resultado: dict[str, Any] = {"resultado": "negada"}
        else:
            registrada = _ACOES.get(linha["acao"])
            if registrada is None:
                raise RuntimeError("Ação sem executor no consumo.")
            parametros = json.loads(linha["parametros_json"])
            resultado = registrada.executar(connection, apartamento, parametros)
            if resultado.get("resultado") not in {"reservada", "indisponivel", "autorizada", "negada"}:
                raise RuntimeError("Executor devolveu resultado fora do contrato.")
        connection.execute(
            text(
                """
                UPDATE decisao_confirmacao
                SET consumida_em = :consumida_em, resultado_json = :resultado_json
                WHERE proposta_id = :proposta_id AND consumida_em IS NULL
                """
            ),
            {
                "consumida_em": _agora(),
                "resultado_json": _json(resultado),
                "proposta_id": proposta_id,
            },
        )
    return resultado
