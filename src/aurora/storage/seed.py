"""Carga inicial transacional. Reiniciar não restaura dados já gravados.

C07: carga inicial ocorre em uma transação somente no banco nunca
inicializado; reiniciar não restaura dados.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from aurora.storage.schema import apply_schema


def initialize_storage(engine: Engine, dados_dir: Path) -> None:
    apply_schema(engine)
    _seed_if_needed(engine, dados_dir)


def _seed_if_needed(engine: Engine, dados_dir: Path) -> None:
    with engine.begin() as connection:
        ready = connection.execute(
            text("SELECT 1 FROM metadado WHERE chave = 'inicializado'")
        ).first()
        if ready is not None:
            return
        _importar(connection, dados_dir)
        connection.execute(
            text(
                "INSERT INTO metadado (chave, valor) "
                "VALUES ('inicializado', '1')"
            )
        )


def _centavos(valor: object) -> int:
    quantia = Decimal(str(valor))
    centavos = (quantia * Decimal(100)).quantize(Decimal("1"))
    if quantia * Decimal(100) != centavos or centavos < 0:
        raise ValueError("Taxa de área inválida no cadastro inicial.")
    return int(centavos)


def _data_civil(valor: object) -> str:
    if not isinstance(valor, str):
        raise ValueError("Data do cadastro inicial inválida.")
    datetime.strptime(valor, "%Y-%m-%d")
    return valor


def _ler(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Cadastro inválido em {path.name}.")
    return payload


def _importar(connection: Connection, dados_dir: Path) -> None:
    apartamentos = _ler(dados_dir / "apartamentos.json")
    areas = _ler(dados_dir / "areas.json")
    reservas = _ler(dados_dir / "reservas.json")
    visitantes = _ler(dados_dir / "visitantes.json")

    for item in apartamentos:
        connection.execute(
            text(
                "INSERT INTO apartamento (numero, morador) VALUES "
                "(:numero, :morador)"
            ),
            {"numero": item["numero"], "morador": item["morador"]},
        )
    for item in areas:
        connection.execute(
            text(
                "INSERT INTO area (id, nome, taxa_centavos) VALUES "
                "(:id, :nome, :taxa_centavos)"
            ),
            {
                "id": item["id"],
                "nome": item["nome"],
                "taxa_centavos": _centavos(item["taxa"]),
            },
        )
    for item in reservas:
        connection.execute(
            text(
                "INSERT INTO reserva (codigo, apartamento, area, data, cancelada) "
                "VALUES (:codigo, :apartamento, :area, :data, 0)"
            ),
            {
                "codigo": item["codigo"],
                "apartamento": item["apartamento"],
                "area": item["area"],
                "data": _data_civil(item["data"]),
            },
        )
    for item in visitantes:
        connection.execute(
            text(
                "INSERT INTO visitante (apartamento, nome, data) VALUES "
                "(:apartamento, :nome, :data)"
            ),
            {
                "apartamento": item["apartamento"],
                "nome": item["nome"],
                "data": _data_civil(item["data"]),
            },
        )

    conferencias = (
        ("SELECT COUNT(*) FROM apartamento", len(apartamentos)),
        ("SELECT COUNT(*) FROM area", len(areas)),
        ("SELECT COUNT(*) FROM reserva", len(reservas)),
        ("SELECT COUNT(*) FROM visitante", len(visitantes)),
    )
    for consulta, esperado in conferencias:
        obtido = connection.execute(text(consulta)).scalar_one()
        if obtido != esperado:
            raise RuntimeError("Carga inicial incompleta.")
