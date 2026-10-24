"""Restauração explícita com a API parada.

C501: o marcador durável é criado antes de qualquer alteração; enquanto
existir, o serviço recusa iniciar; removê-lo exige as duas bases
restauradas e verificadas.
C502: a restauração exige API parada e lock exclusivo; apaga sessões e
eventos, elimina pendências e decisões, repõe reservas e visitantes
iniciais sem editar dados/.
C503: preserva todos os códigos emitidos e o contador monotônico.

Não há commit distribuído entre o banco de negócio e o banco do ADK.
`AURORA_RESET_INTERRUPT` é o ponto de parada do implementador
(`before-commit`, `after-business`, `after-adk`). Não é rota e não conclui
a restauração.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.engine import Engine

from aurora.config import Settings
from aurora.runtime.sessions import recriar_banco_vazio
from aurora.storage.codigos import registrar_codigos_existentes
from aurora.storage.database import dispose_engine
from aurora.storage.database import get_engine
from aurora.storage.maintenance import LOCK_NAME
from aurora.storage.maintenance import LockOcupado
from aurora.storage.maintenance import OperationLock
from aurora.storage.maintenance import remove_marker
from aurora.storage.maintenance import write_marker
from aurora.storage.schema import apply_schema
from aurora.storage.seed import _centavos
from aurora.storage.seed import _data_civil
from aurora.storage.seed import _ler
from aurora.storage.seed import garantir_cadastros
from aurora.storage.seed import inserir_operacionais_iniciais

_FONTES = (
    "apartamentos.json",
    "areas.json",
    "reservas.json",
    "visitantes.json",
)
_FILHOS = (
    "visitante",
    "reserva",
    "despacho_retomada",
    "decisao_confirmacao",
    "proposta_confirmacao",
    "session_identity",
)
_VAZIAS = (
    "session_identity",
    "proposta_confirmacao",
    "decisao_confirmacao",
    "despacho_retomada",
)
_PONTOS = frozenset({"before-commit", "after-business", "after-adk"})
_SUFIXO = re.compile(r"^RSV-(\d+)$")
_TABELAS_ADK = ("sessions", "events", "app_states", "user_states")


class RestauracaoErro(Exception):
    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class RestauracaoInterrompida(Exception):
    def __init__(self, ponto: str):
        super().__init__(ponto)
        self.ponto = ponto


@dataclass(frozen=True)
class _Antes:
    codigos: frozenset[str]
    proximo: int | None
    apartamentos: tuple[tuple[str, str], ...]
    areas: tuple[tuple[str, str, int], ...]


def executar_restauracao(settings: Settings) -> None:
    """Reposição idempotente. Sucesso só depois de conferir os dois bancos."""
    data_dir = settings.data_dir
    lock = OperationLock(data_dir / LOCK_NAME)
    try:
        lock.acquire_exclusive()
    except LockOcupado:
        raise RestauracaoErro(
            "A API está em execução ou outra restauração está ativa. "
            "Nada foi alterado. Pare o processo com Ctrl+C, aguarde o "
            "encerramento e repita: uv run aurora restaurar"
        ) from None
    try:
        _validar_fontes(settings.dados_dir)
        ponto = _ponto_interrupcao()
        hashes = _hashes(settings.dados_dir)
        write_marker(data_dir)
        try:
            _executar(settings, ponto, hashes)
        except RestauracaoInterrompida as exc:
            raise RestauracaoErro(
                "Restauração interrompida após o marcador "
                f"({exc.ponto}). A API não sobe enquanto ele existir. "
                "Com a API parada, repita: uv run aurora restaurar"
            ) from None
        except RestauracaoErro:
            raise
        except Exception as exc:
            raise RestauracaoErro(
                "A restauração falhou depois do marcador "
                f"({type(exc).__name__}). A API não sobe enquanto ele "
                "existir. Com a API parada, repita: uv run aurora restaurar"
            ) from None
    finally:
        lock.release()


def _executar(settings: Settings, ponto: str, hashes: tuple[tuple[str, str], ...]) -> None:
    engine = get_engine()
    try:
        antes = _reset_negocio(engine, settings.dados_dir, ponto)
    finally:
        dispose_engine()
    if ponto == "after-business":
        raise RestauracaoInterrompida(ponto)
    recriar_banco_vazio(settings.adk_db_path)
    if ponto == "after-adk":
        raise RestauracaoInterrompida(ponto)
    engine = get_engine()
    try:
        with engine.connect() as connection:
            _conferir_negocio(connection, settings.dados_dir, antes)
    finally:
        dispose_engine()
    _conferir_adk(settings.adk_db_path)
    if _hashes(settings.dados_dir) != hashes:
        raise RestauracaoErro(
            "Os arquivos iniciais foram alterados durante a restauração. "
            "O marcador permanece. Nada em dados/ deve ser editado."
        )
    remove_marker(settings.data_dir)


def _reset_negocio(engine: Engine, dados_dir: Path, ponto: str) -> _Antes:
    apply_schema(engine)
    with engine.begin() as connection:
        antes = _snapshot(connection)
        for tabela in _FILHOS:
            connection.execute(text(f"DELETE FROM {tabela}"))
        garantir_cadastros(connection, dados_dir)
        inserir_operacionais_iniciais(connection, dados_dir)
        registrar_codigos_existentes(connection)
        connection.execute(
            text(
                "INSERT INTO metadado (chave, valor) VALUES ('inicializado', '1') "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor"
            )
        )
        _conferir_negocio(connection, dados_dir, antes)
        if ponto == "before-commit":
            raise RestauracaoInterrompida(ponto)
    return antes


def _snapshot(connection: Connection) -> _Antes:
    codigos = connection.execute(text("SELECT codigo FROM ledger_codigo")).all()
    proximo = connection.execute(
        text("SELECT proximo FROM sequencia_codigo WHERE chave = 'reserva'")
    ).scalar()
    apartamentos = connection.execute(
        text("SELECT numero, morador FROM apartamento ORDER BY numero")
    ).all()
    areas = connection.execute(
        text("SELECT id, nome, taxa_centavos FROM area ORDER BY id")
    ).all()
    return _Antes(
        codigos=frozenset(str(linha[0]) for linha in codigos),
        proximo=None if proximo is None else int(proximo),
        apartamentos=tuple((str(linha[0]), str(linha[1])) for linha in apartamentos),
        areas=tuple(
            (str(linha[0]), str(linha[1]), int(linha[2])) for linha in areas
        ),
    )


def _conferir_negocio(connection: Connection, dados_dir: Path, antes: _Antes) -> None:
    atual = _snapshot(connection)
    if antes.apartamentos or antes.areas:
        if atual.apartamentos != antes.apartamentos or atual.areas != antes.areas:
            raise RestauracaoErro("A restauração alteraria o cadastro. O marcador permanece.")
    else:
        _conferir_cadastro_inicial(atual, dados_dir)
    _conferir_reservas(connection, dados_dir)
    _conferir_visitantes(connection, dados_dir)
    for tabela in _VAZIAS:
        total = connection.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar_one()
        if int(total) != 0:
            raise RestauracaoErro(
                "Pendências ou sessões de negócio permaneceram. O marcador permanece."
            )
    if not antes.codigos <= atual.codigos:
        raise RestauracaoErro("O ledger de códigos diminuiu. O marcador permanece.")
    iniciais = {str(item["codigo"]) for item in _ler(dados_dir / "reservas.json")}
    if not iniciais <= atual.codigos:
        raise RestauracaoErro("Código inicial ausente no ledger. O marcador permanece.")
    if atual.proximo is None:
        raise RestauracaoErro("Contador de códigos ausente. O marcador permanece.")
    if antes.proximo is not None and atual.proximo < antes.proximo:
        raise RestauracaoErro("O contador de códigos diminuiu. O marcador permanece.")
    maior = 0
    for codigo in atual.codigos:
        encontrado = _SUFIXO.fullmatch(codigo)
        if encontrado is not None:
            maior = max(maior, int(encontrado.group(1)))
    if atual.proximo <= maior:
        raise RestauracaoErro("O contador não cobre os códigos emitidos. O marcador permanece.")
    marca = connection.execute(
        text("SELECT valor FROM metadado WHERE chave = 'inicializado'")
    ).scalar()
    if marca != "1":
        raise RestauracaoErro("A base de negócio não ficou inicializada. O marcador permanece.")


def _conferir_cadastro_inicial(atual: _Antes, dados_dir: Path) -> None:
    apartamentos = tuple(
        sorted(
            (str(item["numero"]), str(item["morador"]))
            for item in _ler(dados_dir / "apartamentos.json")
        )
    )
    areas = tuple(
        sorted(
            (str(item["id"]), str(item["nome"]), _centavos(item["taxa"]))
            for item in _ler(dados_dir / "areas.json")
        )
    )
    if atual.apartamentos != apartamentos or atual.areas != areas:
        raise RestauracaoErro("O cadastro inicial não foi reposto. O marcador permanece.")


def _conferir_reservas(connection: Connection, dados_dir: Path) -> None:
    esperadas = {
        (
            str(item["codigo"]),
            str(item["apartamento"]),
            str(item["area"]),
            _data_civil(item["data"]),
        )
        for item in _ler(dados_dir / "reservas.json")
    }
    linhas = connection.execute(
        text(
            "SELECT codigo, apartamento, area, data, cancelada, cancelada_em "
            "FROM reserva"
        )
    ).all()
    obtidas = set()
    for codigo, apartamento, area, data, cancelada, cancelada_em in linhas:
        if int(cancelada) != 0 or cancelada_em is not None:
            raise RestauracaoErro(
                "Reserva inicial não ficou ativa. O marcador permanece."
            )
        obtidas.add((str(codigo), str(apartamento), str(area), str(data)))
    if obtidas != esperadas:
        raise RestauracaoErro(
            "As reservas não correspondem aos arquivos iniciais. O marcador permanece."
        )


def _conferir_visitantes(connection: Connection, dados_dir: Path) -> None:
    esperados = {
        (str(item["apartamento"]), str(item["nome"]), _data_civil(item["data"]))
        for item in _ler(dados_dir / "visitantes.json")
    }
    linhas = connection.execute(
        text("SELECT apartamento, nome, data, proposta_id FROM visitante")
    ).all()
    obtidos = set()
    for apartamento, nome, data, proposta_id in linhas:
        if proposta_id is not None:
            raise RestauracaoErro(
                "Visitante inicial ficou ligado a uma proposta. O marcador permanece."
            )
        obtidos.add((str(apartamento), str(nome), str(data)))
    if obtidos != esperados:
        raise RestauracaoErro(
            "Os visitantes não correspondem aos arquivos iniciais. O marcador permanece."
        )


def _conferir_adk(path: Path) -> None:
    if not path.is_file():
        raise RestauracaoErro("O banco de sessões não foi recriado. O marcador permanece.")
    engine = create_engine(
        "sqlite:///" + path.resolve().as_posix(),
        connect_args={"check_same_thread": False},
    )
    try:
        with engine.connect() as connection:
            for tabela in _TABELAS_ADK:
                total = connection.execute(
                    text(f"SELECT COUNT(*) FROM {tabela}")
                ).scalar_one()
                if int(total) != 0:
                    raise RestauracaoErro(
                        "O banco de sessões não ficou vazio. O marcador permanece."
                    )
    finally:
        engine.dispose()


def _validar_fontes(dados_dir: Path) -> None:
    if not dados_dir.is_dir():
        raise RestauracaoErro("Diretório de dados iniciais ausente. Nada foi alterado.")
    for nome in _FONTES:
        path = dados_dir / nome
        if not path.is_file():
            raise RestauracaoErro(f"Arquivo inicial ausente ({nome}). Nada foi alterado.")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise RestauracaoErro(f"Arquivo inicial inválido ({nome}). Nada foi alterado.") from None
        if not isinstance(payload, list):
            raise RestauracaoErro(f"Arquivo inicial inválido ({nome}). Nada foi alterado.")


def _ponto_interrupcao() -> str:
    valor = os.environ.get("AURORA_RESET_INTERRUPT", "").strip()
    if not valor:
        return ""
    if valor not in _PONTOS:
        raise RestauracaoErro(
            "Interrupção de restauração desconhecida. Nada foi alterado."
        )
    return valor


def _hashes(dados_dir: Path) -> tuple[tuple[str, str], ...]:
    itens: list[tuple[str, str]] = []
    for path in sorted(item for item in dados_dir.iterdir() if item.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        itens.append((path.name, digest))
    return tuple(itens)
