"""DTOs JSON do contrato HTTP.

A confirmação aceita somente id e um booleano estrito. Apartamento, autor
e parâmetros da proposta não entram nesse corpo.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, model_validator


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

    @model_validator(mode="after")
    def _visitante_publico(self) -> ConfirmacaoPendente:
        """Pendência de acesso expõe só nome e data, sem metadados internos."""
        if self.acao != "autorizar_visitante":
            return self
        nome = self.detalhes.get("nome")
        data = self.detalhes.get("data")
        if set(self.detalhes) != {"nome", "data"}:
            raise ValueError("Pendência de visitante com campos internos.")
        if not isinstance(nome, str) or not nome or not isinstance(data, str) or not data:
            raise ValueError("Pendência de visitante incompleta.")
        return self


class MensagemResponse(BaseModel):
    resposta: str
    confirmacoes_pendentes: list[ConfirmacaoPendente] = Field(default_factory=list)


class ConfirmacaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # ID vazio não está pendente: segue para a decisão e recebe 409.
    id: StrictStr
    confirmado: StrictBool


class ReservaOut(BaseModel):
    codigo: str
    area: str
    data: str


class VisitanteOut(BaseModel):
    nome: str
    data: str
