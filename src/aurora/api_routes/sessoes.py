"""Sessão, mensagem e eventos. Sessão ausente responde 404 antes do modelo."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse

from aurora.errors import ApartamentoInexistente
from aurora.errors import SessaoInexistente
from aurora.schemas import CriarSessaoRequest
from aurora.schemas import CriarSessaoResponse
from aurora.schemas import MensagemRequest
from aurora.schemas import MensagemResponse

router = APIRouter()


def _runtime(request: Request):
    return request.app.state.runtime


@router.post("/sessoes", status_code=201, response_model=CriarSessaoResponse)
async def criar_sessao(corpo: CriarSessaoRequest, request: Request) -> CriarSessaoResponse:
    try:
        session_id = await _runtime(request).criar_sessao(corpo.apartamento)
    except ApartamentoInexistente:
        raise HTTPException(status_code=422, detail="Apartamento inexistente") from None
    return CriarSessaoResponse(session_id=session_id)


@router.post(
    "/sessoes/{session_id}/mensagens",
    response_model=MensagemResponse,
)
async def enviar_mensagem(
    session_id: str,
    corpo: MensagemRequest,
    request: Request,
) -> MensagemResponse:
    try:
        return await _runtime(request).enviar_mensagem(session_id, corpo.texto)
    except SessaoInexistente:
        raise HTTPException(status_code=404, detail="Sessão não encontrada") from None


@router.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str, request: Request) -> JSONResponse:
    try:
        eventos = await _runtime(request).listar_eventos(session_id)
    except SessaoInexistente:
        raise HTTPException(status_code=404, detail="Sessão não encontrada") from None
    return JSONResponse(content=eventos)
