"""Esquema do banco de negócio e bloqueio de mutação da identidade.

As frases C01–C06 são as regras literais do modelo de dados. A carga inicial
e a imutabilidade da sessão também estão impostas aqui, não no prompt.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

# C01: numero é obrigatório e único; morador reproduz o cadastro inicial.
# C02: id é obrigatório e único; nome e taxa reproduzem dados/areas.json;
# taxa zero significa ausência de cobrança.
# C03: session_id é obrigatório e único; apartamento é obrigatório, definido
# uma vez e imutável.
# C04: codigo é obrigatório e único; apartamento e area são obrigatórios e
# referenciam cadastros; data usa AAAA-MM-DD e é uma data civil válida.
# C05: codigo nunca é reutilizado; cancelamentos preservam o registro.
# C06: apartamento, nome e data são obrigatórios; data usa AAAA-MM-DD e é
# uma data civil válida.
SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS apartamento (
        numero TEXT NOT NULL PRIMARY KEY,
        morador TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS area (
        id TEXT NOT NULL PRIMARY KEY,
        nome TEXT NOT NULL,
        taxa_centavos INTEGER NOT NULL CHECK (taxa_centavos >= 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS session_identity (
        session_id TEXT NOT NULL PRIMARY KEY,
        apartamento TEXT NOT NULL REFERENCES apartamento (numero),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reserva (
        codigo TEXT NOT NULL PRIMARY KEY,
        apartamento TEXT NOT NULL REFERENCES apartamento (numero),
        area TEXT NOT NULL REFERENCES area (id),
        data TEXT NOT NULL CHECK (
            data GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(data) = data
        ),
        cancelada INTEGER NOT NULL DEFAULT 0 CHECK (cancelada IN (0, 1))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS visitante (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        apartamento TEXT NOT NULL REFERENCES apartamento (numero),
        nome TEXT NOT NULL,
        data TEXT NOT NULL CHECK (
            data GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(data) = data
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metadado (
        chave TEXT NOT NULL PRIMARY KEY,
        valor TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS session_identity_imutavel
    BEFORE UPDATE ON session_identity
    BEGIN
        SELECT RAISE(ABORT, 'session_identity e imutavel');
    END
    """,
)


def apply_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(text(statement))
