"""DTOs JSON do contrato HTTP.

A confirmação aceita somente id e um booleano estrito. Apartamento, autor
e parâmetros da proposta não entram nesse corpo.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr


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


class ConfirmacaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: StrictStr = Field(min_length=1)
    confirmado: StrictBool


class ReservaOut(BaseModel):
    codigo: str
    area: str
    data: str


class VisitanteOut(BaseModel):
    nome: str
    data: str
