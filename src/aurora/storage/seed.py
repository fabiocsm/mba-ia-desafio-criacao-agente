"""Carga inicial transacional. Reiniciar não restaura dados já gravados.

C07: carga inicial ocorre em uma transação somente no banco nunca
inicializado; reiniciar não restaura dados. A reposição explícita fica em
aurora.storage.reset e não é chamada daqui.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from aurora.storage.codigos import registrar_codigos_existentes
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


def garantir_cadastros(connection: Connection, dados_dir: Path) -> None:
    """Importa apartamentos e áreas só quando o banco ainda não tem cadastro."""
    apartamentos = connection.execute(
        text("SELECT COUNT(*) FROM apartamento")
    ).scalar_one()
    areas = connection.execute(text("SELECT COUNT(*) FROM area")).scalar_one()
    if int(apartamentos) == 0 and int(areas) == 0:
        _inserir_cadastros(connection, dados_dir)
        return
    if int(apartamentos) == 0 or int(areas) == 0:
        raise RuntimeError("Cadastro inicial incompleto.")


def inserir_operacionais_iniciais(connection: Connection, dados_dir: Path) -> None:
    """Reinsere reservas e visitantes iniciais com proposta_id nulo.

    O gatilho que exige proposta vale depois da marca de inicialização.
    A reposição desliga esse gatilho só nesta transação e o recria em seguida.
    """
    from aurora.storage.schema import _garantir_gatilhos_visitante

    connection.execute(text("DROP TRIGGER IF EXISTS visitante_nova_exige_proposta"))
    _inserir_reservas(connection, dados_dir)
    _inserir_visitantes(connection, dados_dir)
    _garantir_gatilhos_visitante(connection)


def _inserir_cadastros(connection: Connection, dados_dir: Path) -> None:
    for item in _ler(dados_dir / "apartamentos.json"):
        connection.execute(
            text(
                "INSERT INTO apartamento (numero, morador) VALUES "
                "(:numero, :morador)"
            ),
            {"numero": item["numero"], "morador": item["morador"]},
        )
    for item in _ler(dados_dir / "areas.json"):
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


def _inserir_reservas(connection: Connection, dados_dir: Path) -> None:
    for item in _ler(dados_dir / "reservas.json"):
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


def _inserir_visitantes(connection: Connection, dados_dir: Path) -> None:
    for item in _ler(dados_dir / "visitantes.json"):
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


def _importar(connection: Connection, dados_dir: Path) -> None:
    apartamentos = _ler(dados_dir / "apartamentos.json")
    areas = _ler(dados_dir / "areas.json")
    reservas = _ler(dados_dir / "reservas.json")
    visitantes = _ler(dados_dir / "visitantes.json")
    _inserir_cadastros(connection, dados_dir)
    _inserir_reservas(connection, dados_dir)
    _inserir_visitantes(connection, dados_dir)
    registrar_codigos_existentes(connection)
    conferencias = (
        ("SELECT COUNT(*) FROM apartamento", len(apartamentos)),
        ("SELECT COUNT(*) FROM area", len(areas)),
        ("SELECT COUNT(*) FROM reserva", len(reservas)),
        ("SELECT COUNT(*) FROM visitante", len(visitantes)),
        ("SELECT COUNT(*) FROM ledger_codigo", len(reservas)),
    )
    for consulta, esperado in conferencias:
        obtido = connection.execute(text(consulta)).scalar_one()
        if obtido != esperado:
            raise RuntimeError("Carga inicial incompleta.")
