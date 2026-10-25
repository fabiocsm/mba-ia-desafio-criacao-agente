"""Tipos internos da consulta. Nenhum deles carrega o arquivo inteiro."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FONTE_RELATIVA = "dados/regulamento.md"

StatusConsulta = Literal["ok", "esclarecer", "sem_base"]


@dataclass(frozen=True)
class Unidade:
    """Uma unidade estrutural já existente na fonte, com o texto literal dela."""

    id: str
    texto: str

    def __repr__(self) -> str:
        return f"Unidade(id={self.id!r})"


@dataclass(frozen=True)
class Indice:
    """Índice reconstruível. A representação não inclui o corpo das unidades."""

    unidades: tuple[Unidade, ...]
    capitulos: int
    artigos: int

    def __repr__(self) -> str:
        return (
            f"Indice(capitulos={self.capitulos}, artigos={self.artigos}, "
            f"unidades={len(self.unidades)})"
        )

    def ids(self) -> set[str]:
        return {unidade.id for unidade in self.unidades}


@dataclass(frozen=True)
class Autorizacao:
    """Conjunto fechado decidido antes do Runner. Sem texto normativo."""

    status: StatusConsulta
    unidades: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in ("ok", "esclarecer", "sem_base"):
            raise ValueError("status inválido")
        if self.status != "ok" and self.unidades:
            raise ValueError("unidades somente com status ok")
        if self.status == "ok" and not self.unidades:
            raise ValueError("status ok exige unidades")


@dataclass(frozen=True)
class ConsultaScope:
    """Escopo de uma execução HTTP. O nonce não é o invocation_id do ADK."""

    session_id: str
    execution_nonce: str
    unidades: frozenset[str]
    status: StatusConsulta

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id obrigatório")
        if not self.execution_nonce:
            raise ValueError("execution_nonce obrigatório")
        if self.status not in ("ok", "esclarecer", "sem_base"):
            raise ValueError("status inválido")
        if self.status != "ok" and self.unidades:
            raise ValueError("unidades somente com status ok")
        if self.status == "ok" and not self.unidades:
            raise ValueError("status ok exige unidades")
