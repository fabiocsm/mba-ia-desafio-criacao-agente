"""Consultas autorizadas.

C12: consulta própria filtra apartamento antes de materializar resultado;
disponibilidade retorna somente livre ou ocupada.

As rotas diretas do avaliador reutilizam as mesmas projeções, com o
apartamento vindo do caminho HTTP. Elas não são ferramentas do agente.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def listar_reservas_ativas(engine: Engine, apartamento: str) -> list[dict[str, str]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT codigo, area, data
                FROM reserva
                WHERE apartamento = :apartamento AND cancelada = 0
                ORDER BY data, codigo
                """
            ),
            {"apartamento": apartamento},
        ).mappings()
        return [
            {"codigo": row["codigo"], "area": row["area"], "data": row["data"]}
            for row in rows
        ]


def listar_visitantes(engine: Engine, apartamento: str) -> list[dict[str, str]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT nome, data
                FROM visitante
                WHERE apartamento = :apartamento
                ORDER BY data, nome, id
                """
            ),
            {"apartamento": apartamento},
        ).mappings()
        return [{"nome": row["nome"], "data": row["data"]} for row in rows]


def resolver_area(engine: Engine, referencia: str) -> str | None:
    """Resolve id ou nome oficial da área. Não lê reservas nem moradores."""
    chave = referencia.strip()
    if not chave:
        return None
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT id, nome FROM area")).mappings().all()
    encontrados = [
        row["id"]
        for row in rows
        if row["id"] == chave or str(row["nome"]).casefold() == chave.casefold()
    ]
    if len(encontrados) != 1:
        return None
    return encontrados[0]


def disponibilidade(engine: Engine, area_id: str, data: str) -> str:
    with engine.connect() as connection:
        ocupada = connection.execute(
            text(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM reserva
                    WHERE area = :area AND data = :data AND cancelada = 0
                )
                """
            ),
            {"area": area_id, "data": data},
        ).scalar_one()
    return "ocupada" if ocupada else "livre"
