"""Ledger e contador duráveis dos códigos de reserva.

C205: codigo do ledger é obrigatório e único; códigos iniciais, cancelados
e emitidos permanecem reservados, inclusive após reinício ou restauração.
C206: proximo é inteiro maior que os sufixos iniciais e avança atomicamente
com a emissão; nenhum código emitido é reutilizado.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

_CHAVE = "reserva"
_SUFIXO = re.compile(r"^RSV-(\d+)$")


def _sufixo(codigo: str) -> int | None:
    encontrado = _SUFIXO.fullmatch(codigo)
    if encontrado is None:
        return None
    return int(encontrado.group(1))


def _maior_sufixo(connection: Connection) -> int:
    linhas = connection.execute(text("SELECT codigo FROM ledger_codigo")).all()
    maior = 0
    for (codigo,) in linhas:
        valor = _sufixo(str(codigo))
        if valor is not None and valor > maior:
            maior = valor
    return maior


def garantir_sequencia(connection: Connection) -> None:
    """Sobe o contador para ficar acima de todo sufixo já reservado."""
    minimo = _maior_sufixo(connection) + 1
    if minimo < 1:
        minimo = 1
    atual = connection.execute(
        text("SELECT proximo FROM sequencia_codigo WHERE chave = :chave"),
        {"chave": _CHAVE},
    ).scalar()
    if atual is None:
        connection.execute(
            text(
                "INSERT INTO sequencia_codigo (chave, proximo) "
                "VALUES (:chave, :proximo)"
            ),
            {"chave": _CHAVE, "proximo": minimo},
        )
        return
    if int(atual) < minimo:
        connection.execute(
            text(
                "UPDATE sequencia_codigo SET proximo = :proximo "
                "WHERE chave = :chave"
            ),
            {"chave": _CHAVE, "proximo": minimo},
        )


def registrar_codigos_existentes(connection: Connection) -> None:
    """Copia códigos já gravados para o ledger e ajusta o contador.

    Não apaga reservas. Pode ser chamada de novo: o que já está no ledger
    permanece.
    """
    agora = datetime.now(timezone.utc).isoformat()
    connection.execute(
        text(
            """
            INSERT INTO ledger_codigo (codigo, emitido_em)
            SELECT reserva.codigo, :agora
            FROM reserva
            WHERE NOT EXISTS (
                SELECT 1 FROM ledger_codigo
                WHERE ledger_codigo.codigo = reserva.codigo
            )
            """
        ),
        {"agora": agora},
    )
    garantir_sequencia(connection)


def emitir_codigo(connection: Connection) -> str:
    """Reserva o próximo RSV-{numero} nesta conexão, sem reutilizar o ledger."""
    atual = connection.execute(
        text("SELECT proximo FROM sequencia_codigo WHERE chave = :chave"),
        {"chave": _CHAVE},
    ).scalar()
    if atual is None:
        raise RuntimeError("Sequência de códigos não inicializada.")
    numero = int(atual)
    while True:
        codigo = f"RSV-{numero}"
        ocupado = connection.execute(
            text("SELECT 1 FROM ledger_codigo WHERE codigo = :codigo"),
            {"codigo": codigo},
        ).first()
        if ocupado is None:
            break
        numero += 1
    connection.execute(
        text(
            "INSERT INTO ledger_codigo (codigo, emitido_em) "
            "VALUES (:codigo, :emitido_em)"
        ),
        {
            "codigo": codigo,
            "emitido_em": datetime.now(timezone.utc).isoformat(),
        },
    )
    connection.execute(
        text(
            "UPDATE sequencia_codigo SET proximo = :proximo WHERE chave = :chave"
        ),
        {"chave": _CHAVE, "proximo": numero + 1},
    )
    return codigo
