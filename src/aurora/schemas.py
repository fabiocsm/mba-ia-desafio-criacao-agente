"""DTOs JSON do contrato HTTP da spec 001.

Listas saem sem envelope. Nesta entrega não há pendências, e o formato já
reserva id, acao e detalhes para a spec 002.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CriarSessaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    apartamento: str


class CriarSessaoResponse(BaseModel):
    session_id: str


class MensagemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str


class ConfirmacaoPendente(BaseModel):
    id: str
    acao: str
    detalhes: dict[str, Any]


class MensagemResponse(BaseModel):
    resposta: str
    confirmacoes_pendentes: list[ConfirmacaoPendente] = Field(default_factory=list)


class ReservaOut(BaseModel):
    codigo: str
    area: str
    data: str


class VisitanteOut(BaseModel):
    nome: str
    data: str
