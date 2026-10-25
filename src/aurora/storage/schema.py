"""Esquema do banco de negócio e bloqueio de mutação da identidade.

As frases C01–C06 vêm da spec 001. C201–C211 desta entrega estão impostas
no esquema e nos repositórios, não no prompt.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

# C01: numero é obrigatório e único; morador reproduz o cadastro inicial.
# C02: id é obrigatório e único; nome e taxa reproduzem dados/areas.json;
# taxa zero significa ausência de cobrança.
# C03: session_id é obrigatório e único; apartamento é obrigatório, definido
# uma vez e imutável.
# C04/C201: codigo é obrigatório, único e gerado pelo sistema; apartamento e
# area são obrigatórios e referenciam cadastros; data usa AAAA-MM-DD e é uma
# data civil válida.
# C05/C202: cancelada é booleano não nulo com default false; cancelar preserva
# a linha e o codigo; cancelada_em é nulo enquanto ativa e preenchido ao
# cancelar. codigo nunca é reutilizado.
# C06/C301: id é obrigatório, único e gerado pelo sistema; apartamento, nome
# e data são obrigatórios; nome não pode ser vazio; data usa AAAA-MM-DD e é
# uma data civil válida.
# C302: proposta_id é nulo para dados iniciais e obrigatório para novas
# autorizações; proposta_id não nulo é único e referencia proposta da mesma
# sessão e ação autorizar_visitante. Não há UNIQUE de nome/data.
# C203: há no máximo uma reserva ativa por area e data, imposta por índice
# único parcial WHERE cancelada=0.
# C205: codigo do ledger é obrigatório e único; códigos iniciais, cancelados
# e emitidos permanecem reservados, inclusive após reinício ou restauração.
# C206: proximo é inteiro maior que os sufixos iniciais e avança atomicamente
# com a emissão; nenhum código emitido é reutilizado.
# C207–C211: proposta, decisão e despacho. Ver data-model da spec 002.
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
        cancelada INTEGER NOT NULL DEFAULT 0 CHECK (cancelada IN (0, 1)),
        cancelada_em TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metadado (
        chave TEXT NOT NULL PRIMARY KEY,
        valor TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ledger_codigo (
        codigo TEXT NOT NULL PRIMARY KEY,
        emitido_em TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sequencia_codigo (
        chave TEXT NOT NULL PRIMARY KEY,
        proximo INTEGER NOT NULL CHECK (proximo > 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS proposta_confirmacao (
        id TEXT NOT NULL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES session_identity (session_id),
        acao TEXT NOT NULL CHECK (acao IN ('reservar_area', 'autorizar_visitante')),
        parametros_json TEXT NOT NULL,
        original_function_call_id TEXT NOT NULL,
        native_confirmation_id TEXT UNIQUE,
        invocation_id TEXT NOT NULL,
        author TEXT NOT NULL,
        branch TEXT,
        fase TEXT NOT NULL CHECK (fase IN ('preparando', 'pendente')),
        created_at TEXT NOT NULL,
        UNIQUE (session_id, invocation_id, original_function_call_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS decisao_confirmacao (
        proposta_id TEXT NOT NULL PRIMARY KEY
            REFERENCES proposta_confirmacao (id),
        confirmado INTEGER NOT NULL CHECK (confirmado IN (0, 1)),
        decidida_em TEXT NOT NULL,
        consumida_em TEXT,
        resultado_json TEXT,
        CHECK (
            (consumida_em IS NULL AND resultado_json IS NULL)
            OR (consumida_em IS NOT NULL AND resultado_json IS NOT NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS visitante (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        apartamento TEXT NOT NULL REFERENCES apartamento (numero),
        nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
        data TEXT NOT NULL CHECK (
            data GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(data) = data
        ),
        proposta_id TEXT UNIQUE REFERENCES proposta_confirmacao (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS despacho_retomada (
        proposta_id TEXT NOT NULL PRIMARY KEY
            REFERENCES decisao_confirmacao (proposta_id),
        estado TEXT NOT NULL CHECK (estado IN ('recuperar', 'concluido')),
        ultima_falha TEXT
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS session_identity_imutavel
    BEFORE UPDATE ON session_identity
    BEGIN
        SELECT RAISE(ABORT, 'session_identity e imutavel');
    END
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS reserva_ativa_area_data
    ON reserva (area, data)
    WHERE cancelada = 0
    """,
    """
    CREATE TRIGGER IF NOT EXISTS proposta_campos_imutaveis
    BEFORE UPDATE ON proposta_confirmacao
    FOR EACH ROW
    WHEN OLD.id != NEW.id
      OR OLD.session_id != NEW.session_id
      OR OLD.acao != NEW.acao
      OR OLD.parametros_json != NEW.parametros_json
      OR OLD.original_function_call_id != NEW.original_function_call_id
      OR OLD.invocation_id != NEW.invocation_id
      OR OLD.author != NEW.author
      OR IFNULL(OLD.branch, '') != IFNULL(NEW.branch, '')
      OR OLD.created_at != NEW.created_at
      OR (OLD.fase = 'pendente' AND NEW.fase != OLD.fase)
      OR (
        OLD.native_confirmation_id IS NOT NULL
        AND IFNULL(NEW.native_confirmation_id, '') != OLD.native_confirmation_id
      )
    BEGIN
        SELECT RAISE(ABORT, 'proposta imutavel');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS decisao_imutavel
    BEFORE UPDATE ON decisao_confirmacao
    FOR EACH ROW
    WHEN OLD.proposta_id != NEW.proposta_id
      OR OLD.confirmado != NEW.confirmado
      OR OLD.decidida_em != NEW.decidida_em
      OR (
        OLD.consumida_em IS NOT NULL
        AND (
          OLD.consumida_em != NEW.consumida_em
          OR IFNULL(OLD.resultado_json, '') != IFNULL(NEW.resultado_json, '')
        )
      )
    BEGIN
        SELECT RAISE(ABORT, 'decisao imutavel');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS despacho_concluido_imutavel
    BEFORE UPDATE ON despacho_retomada
    FOR EACH ROW
    WHEN OLD.estado = 'concluido' AND NEW.estado != 'concluido'
    BEGIN
        SELECT RAISE(ABORT, 'despacho concluido imutavel');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS despacho_so_conclui_consumido
    BEFORE UPDATE ON despacho_retomada
    FOR EACH ROW
    WHEN NEW.estado = 'concluido'
      AND OLD.estado != 'concluido'
      AND (
        SELECT consumida_em
        FROM decisao_confirmacao
        WHERE proposta_id = NEW.proposta_id
      ) IS NULL
    BEGIN
        SELECT RAISE(ABORT, 'concluir exige resultado consumido');
    END
    """,
)


def _colunas(connection: Connection, tabela: str) -> set[str]:
    linhas = connection.execute(text(f"PRAGMA table_info({tabela})")).all()
    return {linha[1] for linha in linhas}


def _sql_tabela(connection: Connection, tabela: str) -> str:
    sql = connection.execute(
        text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = :nome"),
        {"nome": tabela},
    ).scalar()
    return sql or ""


def _visitante_atual(connection: Connection) -> bool:
    """C301/C302 já estão no DDL: nome não vazio, proposta única e FK."""
    if "proposta_id" not in _colunas(connection, "visitante"):
        return False
    sql = _sql_tabela(connection, "visitante")
    return "trim(nome)" in sql and "proposta_confirmacao" in sql


def _migrar_visitante(connection: Connection) -> None:
    """Reconstrói visitante antigo sem apagar linhas nem dados/."""
    if _visitante_atual(connection):
        _garantir_gatilhos_visitante(connection)
        return
    tem_proposta = "proposta_id" in _colunas(connection, "visitante")
    connection.execute(text("DROP TRIGGER IF EXISTS visitante_nova_exige_proposta"))
    connection.execute(text("DROP TRIGGER IF EXISTS visitante_imutavel"))
    connection.execute(text("ALTER TABLE visitante RENAME TO visitante_antiga"))
    connection.execute(
        text(
            """
            CREATE TABLE visitante (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apartamento TEXT NOT NULL REFERENCES apartamento (numero),
                nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
                data TEXT NOT NULL CHECK (
                    data GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                    AND date(data) = data
                ),
                proposta_id TEXT UNIQUE REFERENCES proposta_confirmacao (id)
            )
            """
        )
    )
    if tem_proposta:
        connection.execute(
            text(
                """
                INSERT INTO visitante (id, apartamento, nome, data, proposta_id)
                SELECT id, apartamento, nome, data, proposta_id
                FROM visitante_antiga
                """
            )
        )
    else:
        connection.execute(
            text(
                """
                INSERT INTO visitante (id, apartamento, nome, data, proposta_id)
                SELECT id, apartamento, nome, data, NULL
                FROM visitante_antiga
                """
            )
        )
    connection.execute(text("DROP TABLE visitante_antiga"))
    max_id = connection.execute(
        text("SELECT COALESCE(MAX(id), 0) FROM visitante")
    ).scalar_one()
    connection.execute(text("DELETE FROM sqlite_sequence WHERE name = 'visitante'"))
    if max_id:
        connection.execute(
            text("INSERT INTO sqlite_sequence (name, seq) VALUES ('visitante', :seq)"),
            {"seq": max_id},
        )
    _garantir_gatilhos_visitante(connection)


def _garantir_gatilhos_visitante(connection: Connection) -> None:
    """Nova autorização exige proposta depois do seed. A linha não se reescreve."""
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS visitante_nova_exige_proposta
            BEFORE INSERT ON visitante
            WHEN NEW.proposta_id IS NULL
              AND EXISTS (
                SELECT 1 FROM metadado WHERE chave = 'inicializado'
              )
            BEGIN
                SELECT RAISE(ABORT, 'nova autorizacao exige proposta');
            END
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS visitante_imutavel
            BEFORE UPDATE ON visitante
            BEGIN
                SELECT RAISE(ABORT, 'visitante imutavel');
            END
            """
        )
    )


def _migrar(connection: Connection) -> None:
    """Acrescenta colunas e o ledger sem apagar seed, tombstones ou dados/."""
    if "cancelada_em" not in _colunas(connection, "reserva"):
        connection.execute(text("ALTER TABLE reserva ADD COLUMN cancelada_em TEXT"))
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS reserva_preserva_identidade
            BEFORE UPDATE ON reserva
            FOR EACH ROW
            WHEN NEW.codigo != OLD.codigo
              OR NEW.apartamento != OLD.apartamento
              OR NEW.area != OLD.area
              OR NEW.data != OLD.data
              OR (OLD.cancelada = 1 AND NEW.cancelada = 0)
              OR (NEW.cancelada = 0 AND NEW.cancelada_em IS NOT NULL)
              OR (NEW.cancelada = 1 AND NEW.cancelada_em IS NULL)
            BEGIN
                SELECT RAISE(ABORT, 'reserva imutavel ou cancelamento incoerente');
            END
            """
        )
    )
    from aurora.storage.codigos import registrar_codigos_existentes

    registrar_codigos_existentes(connection)
    _migrar_visitante(connection)


def apply_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(text(statement))
        _migrar(connection)
