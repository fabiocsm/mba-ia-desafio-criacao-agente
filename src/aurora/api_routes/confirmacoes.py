"""Confirmação sistêmica. Sessão ausente responde 404 antes do ID."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request

from aurora.api_routes.session_route import SessionRoute
from aurora.errors import ExecucaoExpirada
from aurora.errors import RetomadaIncompleta
from aurora.errors import SessaoInexistente
from aurora.errors import ConfirmacaoConflito
from aurora.schemas import ConfirmacaoRequest
from aurora.schemas import MensagemResponse

router = APIRouter(route_class=SessionRoute)


def _runtime(request: Request):
    return request.app.state.runtime


@router.post(
    "/sessoes/{session_id}/confirmacoes",
    response_model=MensagemResponse,
)
async def confirmar(
    session_id: str, corpo: ConfirmacaoRequest, request: Request
) -> MensagemResponse:
    try:
        return await _runtime(request).confirmar(
            session_id,
            corpo.id,
            corpo.confirmado,
        )
    except SessaoInexistente:
        raise HTTPException(status_code=404, detail="Sessão não encontrada") from None
    except ConfirmacaoConflito:
        raise HTTPException(
            status_code=409,
            detail="Confirmação não está pendente nesta sessão",
        ) from None
    except ExecucaoExpirada:
        raise HTTPException(
            status_code=504,
            detail="Tempo limite de atendimento excedido.",
        ) from None
    except RetomadaIncompleta:
        raise HTTPException(status_code=500, detail="Falha interna.") from None
