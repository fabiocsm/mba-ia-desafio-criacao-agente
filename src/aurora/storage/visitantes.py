"""Efeito da autorização de visitante na transação do consumo.

C304: nova autorização só é inserida com decisão canônica confirmada;
consumo da decisão, resultado e inserção usam a mesma conexão e transação;
negação não insere visitante. Este módulo não abre transação nem faz commit.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.engine import Connection

from aurora.storage.reservas import data_civil


def validar_parametros_visitante(parametros: dict) -> dict[str, str]:
    """Congela nome e data. Apartamento não entra no snapshot."""
    nome = parametros.get("nome")
    data = parametros.get("data")
    if not isinstance(nome, str) or not nome.strip():
        raise ValueError("Parâmetros de visitante inválidos.")
    if not isinstance(data, str) or not data_civil(data.strip()):
        raise ValueError("Parâmetros de visitante inválidos.")
    if set(parametros) - {"nome", "data"}:
        raise ValueError("Parâmetros de visitante inválidos.")
    return {"nome": nome.strip(), "data": data.strip()}


def executar_autorizacao(
    connection: Connection,
    apartamento: str,
    parametros: dict,
    proposta_id: str,
    session_id: str,
) -> dict[str, str]:
    """Insere o visitante do snapshot. Não decide consentimento nem faz commit.

    A proposta tem de ser desta sessão, desta ação e ainda não consumida.
    O apartamento gravado é o da identidade, não um valor do snapshot.
    """
    if not proposta_id or not session_id or not apartamento:
        raise RuntimeError("Proposta ausente no consumo.")
    congelados = validar_parametros_visitante(parametros)
    linha = connection.execute(
        text(
            """
            SELECT proposta.acao, proposta.parametros_json,
                   decisao.confirmado, decisao.consumida_em,
                   identidade.apartamento
            FROM proposta_confirmacao AS proposta
            JOIN decisao_confirmacao AS decisao
              ON decisao.proposta_id = proposta.id
            JOIN session_identity AS identidade
              ON identidade.session_id = proposta.session_id
            WHERE proposta.id = :proposta_id
              AND proposta.session_id = :session_id
              AND proposta.acao = 'autorizar_visitante'
            """
        ),
        {"proposta_id": proposta_id, "session_id": session_id},
    ).mappings().first()
    if linha is None or linha["apartamento"] != apartamento:
        raise RuntimeError("Proposta de visitante não autorizada.")
    if int(linha["confirmado"]) != 1 or linha["consumida_em"] is not None:
        raise RuntimeError("Proposta de visitante não autorizada.")
    gravados = json.loads(linha["parametros_json"])
    if (
        gravados.get("nome") != congelados["nome"]
        or gravados.get("data") != congelados["data"]
    ):
        raise RuntimeError("Snapshot de visitante divergente.")
    connection.execute(
        text(
            """
            INSERT INTO visitante (apartamento, nome, data, proposta_id)
            VALUES (:apartamento, :nome, :data, :proposta_id)
            """
        ),
        {
            "apartamento": apartamento,
            "nome": congelados["nome"],
            "data": congelados["data"],
            "proposta_id": proposta_id,
        },
    )
    return {
        "resultado": "autorizada",
        "nome": congelados["nome"],
        "data": congelados["data"],
    }
